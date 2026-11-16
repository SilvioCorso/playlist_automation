# Serato Playlist Automation
# Playlist importer module - imports tracks from YouTube/Spotify/Amazon Music URLs
# v1.9.4:
#   - Amazon Music: support for user-playlists, playlists, albums, tracks URLs
#     (Amazon Music is a JS SPA, so we use Playwright to render the page and
#     read track attributes from the virtualized <music-image-row> elements)
# v1.9.3:
#   - YouTube: HTML page is now primary (RSS returns only ~15 newest items)
#   - YouTube: parse lockupViewModel (current UI) + playlistVideoRenderer (legacy)
#   - YouTube: robust ytInitialData extraction via bracket matching
# v1.9.2:
#   - SSL fix: uses unverified SSL context for urllib (Windows cert issue)
#   - Spotify: fixed trackList parsing — uses 'title'/'subtitle' fields
#     (Spotify embed uses these instead of 'name'/'artists'/'trackName')
#   - YouTube: improved artist/title extraction and cleaning
#   - Strips "- Topic" from channel names
#   - Removes [Official Music Video], (Original Mix), etc. from titles
#   - Smart artist detection: prefers title's first part if it looks like artist
#   - Detects record labels vs actual artists

import re
import json
import logging
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from typing import List, Optional, Tuple

logger = logging.getLogger('serato.importer')

# Bundled CA certificates — fixes the Windows cert issue that previously forced
# SSL verification off. Falls back to the OS trust store if certifi is absent.
try:
    import certifi
    _CA_BUNDLE = certifi.where()
except ImportError:  # pragma: no cover - certifi is in requirements.txt
    _CA_BUNDLE = None


def _ssl_context() -> ssl.SSLContext:
    """Return a verified SSL context using certifi's CA bundle when available."""
    ctx = ssl.create_default_context(cafile=_CA_BUNDLE)
    # Verification stays ON (check_hostname=True, verify_mode=CERT_REQUIRED).
    return ctx


# Strict hostname whitelist — prevents substring-spoofing (e.g. a URL like
# https://attacker.com/?x=youtube.com must NOT be treated as YouTube).
_YOUTUBE_HOSTS = {
    'youtube.com', 'www.youtube.com', 'youtu.be', 'music.youtube.com', 'm.youtube.com',
}
_SPOTIFY_HOSTS = {'open.spotify.com', 'spotify.com', 'www.spotify.com'}
_AMAZON_SUFFIXES = (
    '.amazon.com', '.amazon.it', '.amazon.de', '.amazon.fr', '.amazon.es', '.amazon.co.uk',
)


def import_playlist_from_url(url: str) -> Tuple[str, List[str]]:
    """Import playlist tracks from a YouTube, Spotify, or Amazon Music URL.

    Routing is based on the parsed hostname (strict match), never on a bare
    substring test, so spoofed URLs cannot reach the fetchers.
    """
    url = url.strip()
    if len(url) > 2048:
        raise ValueError("URL troppo lungo (limite 2048 caratteri).")

    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Schema URL non supportato. Usa http:// o https://")

    host = parsed.netloc.lower()
    # Strip optional 'user@' or port for matching.
    if '@' in host:
        host = host.split('@', 1)[1]
    if ':' in host:
        host = host.split(':', 1)[0]

    if host in _YOUTUBE_HOSTS:
        return ('YouTube', _import_youtube(url))
    if host in _SPOTIFY_HOSTS:
        return ('Spotify', _import_spotify(url))
    if host.endswith(_AMAZON_SUFFIXES) and (host.startswith('music.') or '/music/' in parsed.path):
        return ('Amazon Music', _import_amazon_music(url))

    raise ValueError(
        "URL non supportata.\n\n"
        "Formati supportati:\n"
        "- YouTube: https://www.youtube.com/playlist?list=...\n"
        "- Spotify: https://open.spotify.com/playlist/...\n"
        "- Amazon Music: https://music.amazon.it/user-playlists/... "
        "oppure /playlists/... o /albums/..."
    )


def _fetch_url(url: str, timeout: int = 30) -> str:
    """Fetch URL content using urllib with SSL verification ENABLED (certifi)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36'),
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
    })
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as response:
        return response.read().decode('utf-8', errors='replace')


# ------------------------------------------------------------------
# Text cleaning utilities
# ------------------------------------------------------------------

_JUNK_PATTERNS = [
    re.compile(r'\s*\[Official (?:Music |Lyric )?Video\]', re.IGNORECASE),
    re.compile(r'\s*\[Official Video\]', re.IGNORECASE),
    re.compile(r'\s*\[HD\]', re.IGNORECASE),
    re.compile(r'\s*\[4K\]', re.IGNORECASE),
    re.compile(r'\s*\[(?:Audio|Clip|Video)\]', re.IGNORECASE),
    re.compile(r'\s*\((?:Official (?:Music )?Video|MV|Audio|Clip)\)', re.IGNORECASE),
    re.compile(r'\s*\((?:Official|Audio)\)', re.IGNORECASE),
]


def _clean_youtube_title(title: str) -> str:
    """Remove common YouTube junk from video titles."""
    cleaned = title
    for pattern in _JUNK_PATTERNS:
        cleaned = pattern.sub('', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    cleaned = cleaned.rstrip(' -').strip()
    return cleaned


def _clean_channel_name(channel: str) -> str:
    """Clean YouTube channel/artist name."""
    cleaned = channel.strip()
    cleaned = re.sub(r'\s*[-–—]\s*Topic\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*VEVO\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*Official\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+(?:Records|Music|Label|Entertainment)\s*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned


def _extract_artist_from_title(title: str) -> Tuple[str, str]:
    """Try to split a title into artist and song."""
    if ' - ' in title:
        parts = title.split(' - ', 1)
        left = parts[0].strip()
        right = parts[1].strip()
        left_words = len(left.split())
        if left_words <= 5 and len(left) < 45 and left_words >= 1:
            return (left, right)
        if len(right) < 80:
            return (left, right)

    if ' by ' in title.lower():
        idx = title.lower().index(' by ')
        artist = title[:idx].strip()
        song = title[idx + 4:].strip()
        if artist and song:
            return (artist, song)

    return ("", title)


def _is_likely_channel_not_artist(channel: str, title: str) -> bool:
    """Check if the YouTube channel name is likely a record label."""
    label_keywords = [
        'records', 'music', 'label', 'entertainment', 'publishing',
        'media', 'studio', 'production', 'group', 'radio',
        'tv', 'channel', 'distribution', 'mgmt'
    ]
    channel_lower = channel.lower()
    for kw in label_keywords:
        if kw in channel_lower:
            return True
    return False


def _build_track_entry(raw_title: str, channel: str) -> str:
    """Build a clean 'Artist - Title' string from YouTube data."""
    cleaned_title = _clean_youtube_title(raw_title)
    if not cleaned_title:
        return raw_title

    existing_artist, song = _extract_artist_from_title(cleaned_title)
    if existing_artist:
        return cleaned_title

    clean_channel = _clean_channel_name(channel)
    if not clean_channel or not song:
        return cleaned_title

    if _is_likely_channel_not_artist(clean_channel, cleaned_title):
        return cleaned_title

    if clean_channel.lower() in cleaned_title.lower():
        return cleaned_title

    if len(clean_channel) < 2:
        return cleaned_title

    return f"{clean_channel} - {cleaned_title}"


# ------------------------------------------------------------------
# YouTube import
# ------------------------------------------------------------------

def _import_youtube(url: str) -> List[str]:
    """Extract track names from YouTube playlist."""
    match = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
    if not match:
        raise ValueError(
            "URL YouTube non contiene un ID playlist.\n\n"
            "Assicurati che l'URL contenga ?list=ID_PLAYLIST\n"
            "Esempio: https://www.youtube.com/playlist?list=PLxxxxxx"
        )

    playlist_id = match.group(1)
    logger.info("YouTube playlist ID: %s", playlist_id)

    # Primary: HTML page — contains the full playlist (RSS caps at ~15 items).
    html_url = f"https://www.youtube.com/playlist?list={playlist_id}"
    try:
        html = _fetch_url(html_url)
        titles = _parse_youtube_html(html, playlist_id)
        if titles:
            return titles
    except Exception as e:
        logger.warning("YouTube HTML parse failed: %s", e)

    # Fallback: RSS feed (partial list, but works when HTML layout changes).
    feed_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
    try:
        xml_content = _fetch_url(feed_url)
        titles = _parse_youtube_feed(xml_content)
        if titles:
            logger.warning(
                "YouTube: usato feed RSS parziale (%d brani). "
                "Se mancano titoli, aggiorna l'app.",
                len(titles),
            )
            return titles
    except Exception as e:
        logger.warning("YouTube RSS feed failed: %s", e)

    raise ValueError(
        "Impossibile importare la playlist YouTube.\n\n"
        "Verifica che la playlist sia pubblica e che l'URL sia corretto."
    )


def _parse_youtube_feed(xml_content: str) -> List[str]:
    """Parse YouTube RSS feed XML to extract video titles."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
        raise ValueError(f"Errore nel parsing XML YouTube: {e}")

    ns = {
        'atom': 'http://www.w3.org/2005/Atom',
        'yt': 'http://www.youtube.com/xml/schemas/2015',
        'media': 'http://search.yahoo.com/mrss/',
    }

    titles = []
    for entry in root.findall('atom:entry', ns):
        title_elem = entry.find('atom:title', ns)
        if title_elem is not None and title_elem.text:
            raw_title = title_elem.text.strip()
            author = entry.find('atom:author/atom:name', ns)
            channel = author.text.strip() if author is not None and author.text else ""
            track = _build_track_entry(raw_title, channel)
            titles.append(track)
            logger.info("  YT feed: raw='%s' channel='%s' -> '%s'",
                        raw_title[:50], channel[:30], track[:60])

    if not titles:
        raise ValueError(
            "Nessun brano trovato nel feed YouTube.\n"
            "La playlist potrebbe essere vuota o privata."
        )

    logger.info("YouTube RSS: trovati %d brani", len(titles))
    return titles


def _extract_yt_initial_data(html: str) -> dict:
    """Parse var ytInitialData = {...}; from a YouTube page."""
    marker = "var ytInitialData = "
    start = html.find(marker)
    if start < 0:
        raise ValueError("ytInitialData non trovato nella pagina YouTube.")
    start += len(marker)
    depth = 0
    for i in range(start, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                blob = html[start:i + 1]
                return json.loads(blob)
    raise ValueError("ytInitialData JSON troncato o non valido.")


def _yt_text(node) -> str:
    """Extract plain text from YouTube's text objects (runs / simpleText / content)."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node.strip()
    if isinstance(node, dict):
        if "content" in node and isinstance(node["content"], str):
            return node["content"].strip()
        if "simpleText" in node and isinstance(node["simpleText"], str):
            return node["simpleText"].strip()
        runs = node.get("runs")
        if isinstance(runs, list):
            return "".join(
                r.get("text", "") for r in runs if isinstance(r, dict)
            ).strip()
    return ""


def _extract_lockup_artist(meta: dict) -> str:
    """Artist/channel from lockupMetadataViewModel (2024+ YouTube playlist UI)."""
    rows = (
        meta.get("metadata", {})
        .get("contentMetadataViewModel", {})
        .get("metadataRows", [])
    )
    if rows:
        parts = rows[0].get("metadataParts", [])
        if parts:
            artist = _yt_text(parts[0].get("text"))
            if artist and not re.search(
                r"visualiz|views|visualisation|subscribers|iscritti",
                artist,
                re.IGNORECASE,
            ):
                return _clean_channel_name(artist)

    image = meta.get("image", {})
    avatar = image.get("decoratedAvatarViewModel", {})
    label = avatar.get("a11yLabel", "")
    if label:
        for prefix in ("Vai al canale ", "Go to channel ", "Ir al canal ", "Zum Kanal "):
            if label.startswith(prefix):
                return _clean_channel_name(label[len(prefix):])
        if "canal" in label.lower() or "channel" in label.lower():
            return _clean_channel_name(re.sub(r"^(?:Vai al |Go to )canale\s+", "", label, flags=re.I))
    return ""


def _parse_youtube_playlist_item(item: dict) -> str:
    """Parse one playlist row from ytInitialData (new or legacy format)."""
    if "lockupViewModel" in item:
        lv = item["lockupViewModel"]
        meta = lv.get("metadata", {}).get("lockupMetadataViewModel", {})
        raw_title = _yt_text(meta.get("title"))
        if not raw_title:
            return ""
        channel = _extract_lockup_artist(meta)
        track = _build_track_entry(raw_title, channel)
        logger.info("  YT lockup: raw='%s' channel='%s' -> '%s'",
                    raw_title[:50], channel[:30], track[:60])
        return track

    if "playlistVideoRenderer" in item:
        pvr = item["playlistVideoRenderer"]
        raw_title = _yt_text(pvr.get("title"))
        channel = _yt_text(pvr.get("shortBylineText"))
        if not raw_title:
            return ""
        track = _build_track_entry(raw_title, channel)
        logger.info("  YT renderer: raw='%s' channel='%s' -> '%s'",
                    raw_title[:50], channel[:30], track[:60])
        return track

    return ""


def _youtube_expected_video_count(data: dict) -> Optional[int]:
    """Read total video count from playlist sidebar stats, if present."""
    try:
        stats = (
            data["sidebar"]["playlistSidebarRenderer"]["items"][0]
            ["playlistSidebarPrimaryInfoRenderer"]["stats"]
        )
        for stat in stats:
            text = _yt_text(stat)
            if not text:
                continue
            m = re.match(r"^(\d[\d,\.]*)", text.replace("\xa0", " "))
            if m:
                return int(m.group(1).replace(",", "").replace(".", ""))
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    return None


def _youtube_continuation_token(data: dict) -> str:
    """Extract browse continuation token when playlist has more pages."""
    try:
        sections = (
            data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]
            ["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
        )
    except (KeyError, IndexError, TypeError):
        return ""

    for section in sections:
        for key in ("continuationItemRenderer", "continuationItemViewModel"):
            if key not in section:
                continue
            node = section[key]
            cmd = node.get("continuationEndpoint") or node.get("continuationCommand", {})
            if "innertubeCommand" in cmd:
                cmd = cmd["innertubeCommand"]
            cont = cmd.get("continuationCommand") or cmd.get("nextContinuationData") or {}
            token = cont.get("token") or cont.get("continuation")
            if token:
                return token
    return ""


def _collect_youtube_playlist_items(data: dict) -> List[str]:
    """Walk ytInitialData and collect all playlist video entries."""
    titles: List[str] = []
    try:
        sections = (
            data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]
            ["tabRenderer"]["content"]["sectionListRenderer"]["contents"]
        )
    except (KeyError, IndexError, TypeError):
        return titles

    for section in sections:
        if "itemSectionRenderer" not in section:
            continue
        for item in section["itemSectionRenderer"].get("contents", []):
            track = _parse_youtube_playlist_item(item)
            if track:
                titles.append(track)
    return titles


def _fetch_youtube_continuation(token: str, playlist_id: str) -> dict:
    """Fetch next page of playlist items via YouTube innertube browse API."""
    api_url = "https://www.youtube.com/youtubei/v1/browse?prettyPrint=false"
    payload = json.dumps({
        "context": {
            "client": {
                "clientName": "WEB",
                # NOTE: clientVersion is a synthetic future date. YouTube's innertube
                # API accepts a wide range; if validation tightens and continuations
                # start returning empty, the loop below stops after 3 empty pages.
                "clientVersion": "2.20260101.00.00",
                "hl": "en",
            }
        },
        "continuation": token,
        "browseId": f"VL{playlist_id}",
    }).encode("utf-8")
    req = urllib.request.Request(
        api_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Origin": "https://www.youtube.com",
            "Referer": f"https://www.youtube.com/playlist?list={playlist_id}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30, context=_ssl_context()) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _parse_youtube_continuation_response(data: dict) -> Tuple[List[str], str]:
    """Parse innertube continuation response; return (tracks, next_token)."""
    titles: List[str] = []
    next_token = ""

    endpoints = data.get("onResponseReceivedActions") or data.get("continuationContents", {})
    if isinstance(endpoints, list):
        for action in endpoints:
            cont = action.get("appendContinuationItemsAction", {})
            for item in cont.get("continuationItems", []):
                track = _parse_youtube_playlist_item(item)
                if track:
                    titles.append(track)
                for key in ("continuationItemRenderer", "continuationItemViewModel"):
                    if key in item:
                        node = item[key]
                        cmd = node.get("continuationEndpoint") or node.get("continuationCommand", {})
                        if "innertubeCommand" in cmd:
                            cmd = cmd["innertubeCommand"]
                        cont_cmd = cmd.get("continuationCommand") or {}
                        tok = cont_cmd.get("token")
                        if tok:
                            next_token = tok

    # Legacy continuationContents path
    if not titles and isinstance(endpoints, dict):
        playlist_cont = endpoints.get("playlistVideoListContinuation", {})
        for item in playlist_cont.get("contents", []):
            track = _parse_youtube_playlist_item(item)
            if track:
                titles.append(track)
        cont_renderer = playlist_cont.get("continuations", [{}])
        if cont_renderer:
            next_data = cont_renderer[0].get("nextContinuationData", {})
            next_token = next_data.get("continuation") or next_token

    return titles, next_token


def _import_youtube_all_pages(initial_data: dict, playlist_id: str) -> List[str]:
    """Collect playlist items from initial HTML plus continuation pages."""
    titles = _collect_youtube_playlist_items(initial_data)
    expected = _youtube_expected_video_count(initial_data)
    token = _youtube_continuation_token(initial_data)

    if expected:
        logger.info("YouTube playlist: %d brani attesi, %d dal HTML iniziale",
                    expected, len(titles))

    # Only paginate when the sidebar says there are more items than we parsed.
    empty_streak = 0
    while token and (expected is None or len(titles) < expected):
        logger.info("YouTube: richiesta continuazione (%d/%s)...",
                    len(titles), expected or "?")
        try:
            cont_data = _fetch_youtube_continuation(token, playlist_id)
        except Exception as e:
            logger.warning("YouTube continuation failed: %s", e)
            break
        more, token = _parse_youtube_continuation_response(cont_data)
        if not more:
            empty_streak += 1
            if empty_streak >= 3:
                # YouTube silently changed validation — stop instead of looping.
                logger.warning(
                    "YouTube: 3 continuation pages returned 0 items; "
                    "stopping at %d/%s tracks (clientVersion may need updating).",
                    len(titles), expected or "?")
                break
            continue
        empty_streak = 0
        titles.extend(more)

    return titles


def _parse_youtube_html(html: str, playlist_id: str = "") -> List[str]:
    """Parse YouTube playlist HTML page for all video titles."""
    data = _extract_yt_initial_data(html)
    titles = _import_youtube_all_pages(data, playlist_id)

    if not titles:
        # Last-resort legacy recursive scrape (older page layouts).
        titles = [
            _clean_youtube_title(t)
            for t in _extract_yt_titles_recursive(data)
            if t and len(t) > 2
        ]
        # Deduplicate while preserving order
        seen = set()
        deduped = []
        for t in titles:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        titles = deduped

    if not titles:
        raise ValueError("Impossibile estrarre brani dalla playlist YouTube.")

    logger.info("YouTube HTML: trovati %d brani", len(titles))
    return titles


def _extract_yt_titles_recursive(data, depth=0):
    """Recursively extract video titles from YouTube JSON."""
    if depth > 15 or not isinstance(data, (dict, list)):
        return []

    titles = []
    if isinstance(data, dict):
        if 'title' in data and isinstance(data['title'], dict):
            runs = data['title'].get('runs', [])
            for run in runs:
                text = run.get('text', '').strip()
                if text and len(text) > 2:
                    titles.append(text)
        for value in data.values():
            titles.extend(_extract_yt_titles_recursive(value, depth + 1))
    elif isinstance(data, list):
        for item in data:
            titles.extend(_extract_yt_titles_recursive(item, depth + 1))
    return titles


# ------------------------------------------------------------------
# Spotify import
# ------------------------------------------------------------------

def _import_spotify(url: str) -> List[str]:
    """Extract track names from Spotify playlist."""
    embed_url = url.replace('open.spotify.com/', 'open.spotify.com/embed/')
    embed_url = embed_url.split('?')[0]

    logger.info("Spotify embed URL: %s", embed_url)

    try:
        html = _fetch_url(embed_url)
        return _parse_spotify_embed(html)
    except Exception as e:
        logger.warning("Spotify embed failed: %s", e)
        raise ValueError(
            f"Errore nell'importazione da Spotify: {e}\n\n"
            "Possibili cause:\n"
            "- Playlist privata (deve essere pubblica)\n"
            "- URL non valido\n"
            "- Problema di connessione o firewall"
        )


def _parse_spotify_embed(html: str) -> List[str]:
    """Parse Spotify embed HTML to extract track info.

    Spotify embed JSON structure (current):
      entity.trackList[i].title = track name
      entity.trackList[i].subtitle = artist name(s)

    NOTE: The 'title'/'subtitle' fields are used in the embed page,
    NOT 'trackName'/'artistName'/'name'/'artists' as in the full Spotify app.
    """
    titles = []

    # Method 1: __NEXT_DATA__ JSON — extract via known path
    json_match = re.search(
        r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    if json_match:
        try:
            data = json.loads(json_match.group(1))

            # Direct path: props.pageProps.state.data.entity.trackList
            try:
                entity = data['props']['pageProps']['state']['data']['entity']
                if entity and 'trackList' in entity:
                    track_list = entity['trackList']
                    if isinstance(track_list, list) and track_list:
                        for item in track_list:
                            # Spotify embed uses 'title' = song, 'subtitle' = artist
                            song = item.get('title', '')
                            artist = item.get('subtitle', '')
                            if song:
                                if artist:
                                    titles.append(f"{artist} - {song}")
                                else:
                                    titles.append(song)
                        if titles:
                            logger.info("Spotify trackList: trovati %d brani", len(titles))
                            return titles
            except (KeyError, TypeError) as e:
                logger.warning("Spotify direct path failed: %s", e)

            # Fallback: recursive JSON search
            tracks = _extract_spotify_tracks_recursive(data)
            if tracks:
                logger.info("Spotify recursive: trovati %d brani", len(tracks))
                return tracks

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Spotify __NEXT_DATA__ parse error: %s", e)

    # Method 2: Regex — try title/subtitle pairs (Spotify embed format)
    # Pattern: "title": "SongName", "subtitle": "ArtistName"
    title_sub_pairs = re.findall(
        r'"title"\s*:\s*"([^"]+?)"\s*,\s*"subtitle"\s*:\s*"([^"]+?)"',
        html
    )
    if title_sub_pairs:
        skip_titles = {'Spotify', 'Playlist', 'embed'}
        for song, artist in title_sub_pairs:
            if song and song not in skip_titles:
                titles.append(f"{artist} - {song}")
        if titles:
            logger.info("Spotify regex title/subtitle: trovati %d brani", len(titles))
            return titles

    # Method 3: Regex — try trackName/artistName (older Spotify format)
    track_names = re.findall(r'"trackName"\s*:\s*"([^"]+)"', html)
    artist_names = re.findall(r'"artistName"\s*:\s*"([^"]+)"', html)
    if track_names and artist_names:
        count = min(len(track_names), len(artist_names))
        for i in range(count):
            titles.append(f"{artist_names[i]} - {track_names[i]}")
        if titles:
            logger.info("Spotify regex trackName: trovati %d brani", len(titles))
            return titles

    # Method 4: Last resort — standalone title fields
    all_titles = re.findall(r'"title"\s*:\s*"([^"]+)"', html)
    skip = {'spotify', 'embed', 'playlist', 'home', 'search', 'library',
            'create playlist', 'liked songs', 'your library', 'null', 'Spotify'}
    seen = set()
    for name in all_titles:
        if 3 < len(name) < 150 and name not in skip and name not in seen:
            seen.add(name)
            titles.append(name)

    if not titles:
        raise ValueError(
            "Nessun brano trovato nella playlist Spotify.\n\n"
            "Possibili cause:\n"
            "- Playlist privata\n"
            "- URL non valido\n"
            "- Spotify potrebbe richiedere autenticazione"
        )

    logger.info("Spotify: trovati %d brani", len(titles))
    return titles


def _extract_spotify_tracks_recursive(data, depth=0) -> List[str]:
    """Recursively search for trackList with title/subtitle in Spotify JSON."""
    if depth > 25 or not isinstance(data, (dict, list)):
        return []

    tracks = []

    if isinstance(data, dict):
        # Look for trackList with title/subtitle structure
        if 'trackList' in data:
            track_list = data['trackList']
            if isinstance(track_list, list):
                for item in track_list:
                    if isinstance(item, dict):
                        song = item.get('title', '')
                        artist = item.get('subtitle', '')
                        # Also try name/artists (older format)
                        if not song:
                            song = item.get('name', '')
                        if not artist:
                            artists = item.get('artists', [])
                            if artists and isinstance(artists, list):
                                artist = artists[0].get('name', '') if artists else ''
                        if song:
                            if artist:
                                tracks.append(f"{artist} - {song}")
                            else:
                                tracks.append(song)
                if tracks:
                    return tracks

        # Recurse
        for value in data.values():
            if isinstance(value, (dict, list)):
                tracks.extend(_extract_spotify_tracks_recursive(value, depth + 1))

    elif isinstance(data, list):
        for item in data:
            tracks.extend(_extract_spotify_tracks_recursive(item, depth + 1))

    return tracks


# ------------------------------------------------------------------
# Amazon Music import
# ------------------------------------------------------------------
#
# Amazon Music web (music.amazon.it / music.amazon.com / ...) is a fully
# client-side SPA. The HTML returned by urllib is just a ~11 KB shell with
# a JS bundle reference. The actual playlist contents are loaded
# dynamically by the JS app via XHR calls to
# `https://<region>.web.skill.music.a2z.com/api/showHome` (and friends)
# and then rendered into a virtualized list of <music-image-row> custom
# elements (Web Components with Shadow DOM).
#
# Crucially:
#   - The initial `showHome` JSON response carries the song *title*
#     (`primaryText`) and the album name, but NOT the artist.
#   - The artist name appears only as an attribute `secondary-text-1` on
#     the <music-image-row> element, and only AFTER the row has been
#     scrolled into view (the list is virtualized, so off-screen rows
#     are placeholders without data attributes).
#
# Therefore we MUST render the page with a headless browser, scroll
# through it progressively, and capture each `music-image-row[data-key]`
# element's attributes. Playwright is the only reliable way to do this.

_AMAZON_BROWSERS = ('chromium', 'firefox', 'webkit')


def _import_amazon_music(url: str) -> List[str]:
    """Extract tracks from an Amazon Music URL using a headless browser.

    Supports:
      - user-playlists/<id>
      - playlists/<id>
      - albums/<asin>
      - tracks/<asin>
      - artists/<asin>/<slug>

    Returns a list of ``"artist - title"`` strings (or just ``"title"``
    when the artist is not available).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ValueError(
            "Per importare da Amazon Music è necessario Playwright.\n\n"
            "Installa le dipendenze con:\n"
            "    pip install playwright\n"
            "    playwright install chromium\n\n"
            "Amazon Music è una web app a caricamento JavaScript, quindi "
            "non può essere letta con urllib come YouTube o Spotify."
        )

    logger.info("Amazon Music URL: %s", url)

    tracks = []
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            # Common cause: Chromium binary not installed via
            # `playwright install chromium`
            raise ValueError(
                "Impossibile avviare il browser headless di Playwright.\n\n"
                "Esegui una volta:\n"
                "    playwright install chromium\n\n"
                f"Dettaglio errore: {e}"
            )

        try:
            context = browser.new_context(
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                ),
                viewport={'width': 1280, 'height': 900},
                locale='it-IT',
            )
            page = context.new_page()

            try:
                page.goto(url, wait_until='networkidle', timeout=60000)
            except Exception as e:
                logger.warning("Amazon Music goto warning: %s", e)

            # Give the SPA time to bootstrap and make its initial API calls.
            page.wait_for_timeout(5000)

            # Progressive scroll: the <music-image-row> list is virtualized,
            # so only rows that have been scrolled into view have the
            # `data-key`, `primary-text`, `secondary-text-1` attributes
            # we need. We scroll the window AND any internal scrollable
            # containers, capturing unique rows as they appear.
            all_tracks = {}
            no_progress = 0
            prev_count = 0

            for i in range(120):
                rows = page.evaluate(
                    """() => {
                        const out = [];
                        const rows = document.querySelectorAll('music-image-row[data-key]');
                        for (const r of rows) {
                            out.push({
                                dk: r.getAttribute('data-key'),
                                primary: r.getAttribute('primary-text'),
                                secondary1: r.getAttribute('secondary-text-1'),
                                secondary2: r.getAttribute('secondary-text-2'),
                            });
                        }
                        return out;
                    }"""
                )
                for r in rows:
                    if r.get('dk') and r['dk'] not in all_tracks:
                        all_tracks[r['dk']] = r

                # Scroll the window
                page.evaluate("window.scrollBy(0, 1500)")
                # Also scroll any internal scrollable containers
                page.evaluate(
                    """() => {
                        const all = document.querySelectorAll('*');
                        for (const el of all) {
                            const s = getComputedStyle(el);
                            if ((s.overflowY === 'auto' || s.overflowY === 'scroll')
                                && el.scrollHeight > el.clientHeight + 100) {
                                el.scrollTop += 1500;
                            }
                        }
                    }"""
                )
                page.wait_for_timeout(500)

                if len(all_tracks) == prev_count:
                    no_progress += 1
                    if no_progress >= 10:
                        break
                else:
                    no_progress = 0
                prev_count = len(all_tracks)

            # Final capture after the last scroll
            rows = page.evaluate(
                """() => {
                    const out = [];
                    const rows = document.querySelectorAll('music-image-row[data-key]');
                    for (const r of rows) {
                        out.push({
                            dk: r.getAttribute('data-key'),
                            primary: r.getAttribute('primary-text'),
                            secondary1: r.getAttribute('secondary-text-1'),
                        });
                    }
                    return out;
                }"""
            )
            for r in rows:
                if r.get('dk') and r['dk'] not in all_tracks:
                    all_tracks[r['dk']] = r

            logger.info("Amazon Music: acquisite %d righe uniche", len(all_tracks))

            # Preserve discovery order (the dict is insertion-ordered, which
            # matches the order in which rows became visible during scrolling —
            # but we want playlist order, so we sort by the numeric part of
            # `data-key` if present, otherwise by insertion order).
            #
            # The `data-key` attribute looks like: "<Title><Artist><Album><Index>"
            # where <Index> is the 1-based position in the playlist. We can't
            # reliably parse it because title/artist aren't delimited. Instead,
            # we re-fetch the rows in DOM order, which is the playlist order
            # once everything has been rendered.
            #
            # However: due to virtualization, not all rows are in the DOM at
            # once. We rely on the captured dict; for typical playlists (≤200
            # tracks) the iteration above captures every row at least once.
            #
            # To preserve order, we re-scroll to top and scroll down once more,
            # this time recording the order in which we first see each data-key.
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(800)

            ordered_keys = []
            seen = set()
            no_progress = 0
            prev_seen = 0
            for i in range(120):
                rows = page.evaluate(
                    """() => {
                        const out = [];
                        const rows = document.querySelectorAll('music-image-row[data-key]');
                        for (const r of rows) {
                            out.push(r.getAttribute('data-key'));
                        }
                        return out;
                    }"""
                )
                for dk in rows:
                    if dk and dk not in seen:
                        seen.add(dk)
                        ordered_keys.append(dk)

                page.evaluate("window.scrollBy(0, 1500)")
                page.evaluate(
                    """() => {
                        const all = document.querySelectorAll('*');
                        for (const el of all) {
                            const s = getComputedStyle(el);
                            if ((s.overflowY === 'auto' || s.overflowY === 'scroll')
                                && el.scrollHeight > el.clientHeight + 100) {
                                el.scrollTop += 1500;
                            }
                        }
                    }"""
                )
                page.wait_for_timeout(500)

                if len(seen) == prev_seen:
                    no_progress += 1
                    if no_progress >= 10:
                        break
                else:
                    no_progress = 0
                prev_seen = len(seen)

            # Fallback: if the ordered pass didn't capture all keys (rare),
            # append the missing ones at the end in arbitrary order.
            for dk in all_tracks.keys():
                if dk not in seen:
                    ordered_keys.append(dk)

            # Build the final list in playlist order
            for dk in ordered_keys:
                r = all_tracks.get(dk)
                if not r:
                    continue
                primary = (r.get('primary') or '').strip()
                artist = (r.get('secondary1') or '').strip()
                if not primary:
                    continue
                if artist:
                    tracks.append(f"{artist} - {primary}")
                else:
                    tracks.append(primary)
        finally:
            browser.close()

    if not tracks:
        raise ValueError(
            "Nessun brano trovato nella pagina Amazon Music.\n\n"
            "Possibili cause:\n"
            "- Playlist privata (deve essere pubblica)\n"
            "- URL non valido\n"
            "- La playlist è vuota\n"
            "- Problema di connessione o regione non supportata"
        )

    logger.info("Amazon Music: trovati %d brani", len(tracks))
    return tracks

