import os
import re

import aiohttp
import aiohttp.web_request
from aiohttp import web
from loguru import logger

from cache import post_cache, shareid_cache
from config import config
from internal.grid_layout import grid_from_urls
from internal.singleflight import Singleflight
from scrapers import get_post
from scrapers.share import resolve_share_id
from templates.embed import render_embed


# Hardcoded HOST for Render (must be 0.0.0.0)
HOST = "0.0.0.0"
# Get PORT from environment variable (Render sets this)
PORT = int(os.environ.get("PORT", "3000"))

async def home(request: aiohttp.web_request.Request):
    return web.Response(text="Hello, world")


async def embed(request: aiohttp.web_request.Request):
    ig_url = str(
        request.url.with_host("www.instagram.com").with_port(None).with_scheme("https")
    )
    if not re.search(
        r"(discordbot|telegrambot|facebook|whatsapp|firefox\/92|vkshare|revoltchat|preview|iframely)",
        request.headers.get("User-Agent", "").lower(),
    ):
        return web.Response(status=307, headers={"Location": ig_url})

    post_id = request.match_info.get("post_id", "")
    media_num = int(request.match_info.get("media_num", 0))

    if post_id[0] == "B":
        resolve_id = await resolve_share_id(post_id)
        if resolve_id:
            post_id = resolve_id
        else:
            raise web.HTTPFound(
                f"https://www.instagram.com/p/{post_id}",
            )

    post = await get_post(post_id)
    # logger.debug(f"embed({post_id})")
    # Return to original post if no post found
    if not post:
        raise web.HTTPFound(
            f"https://www.instagram.com/p/{post_id}",
        )

    jinja_ctx = {
        "theme_color": "#0084ff",
        "twitter_title": post.username,
        "og_site_name": "InstaFix",
        "og_url": ig_url,
        "og_description": post.caption,
        "redirect_url": ig_url,
    }
    if media_num == 0 and post.medias[0].type == "GraphImage" and len(post.medias) > 1:
        jinja_ctx["image_url"] = f"/grid/{post.post_id}/"
    elif post.medias[max(1, media_num) - 1].type == "GraphImage":
        jinja_ctx["image_url"] = f"/images/{post.post_id}/{max(1, media_num)}"
    else:
        jinja_ctx["video_url"] = f"/videos/{post.post_id}/{max(1, media_num)}"

    # direct = redirect to media url
    if request.query.get("direct"):
        return web.Response(
            status=307,
            headers={
                "Location": jinja_ctx.get("image_url", jinja_ctx.get("video_url", ""))
            },
        )

    # gallery = no caption
    if request.query.get("gallery"):
        jinja_ctx.pop("og_description", None)

    return web.Response(
        body=render_embed(**jinja_ctx).encode(), content_type="text/html"
    )


async def media_redirect(request: aiohttp.web_request.Request):
    post_id = request.match_info.get("post_id", "")
    media_id = request.match_info.get("media_id", "")
    post = await get_post(post_id)

    # logger.debug(f"media_redirect({post_id})")
    # Return to original post if no post found
    if not post:
        raise web.HTTPFound(
            f"https://www.instagram.com/p/{post_id}",
        )

    media = post.medias[int(media_id) - 1]
    return web.Response(status=307, headers={"Location": media.url})


grid_sf = Singleflight[str, str | None]()


async def grid(request: aiohttp.web_request.Request):
    post_id = request.match_info.get("post_id", "")
    if os.path.exists(f"cache/grid/{post_id}.jpeg"):
        with open(f"cache/grid/{post_id}.jpeg", "rb") as f:
            return web.Response(body=f.read(), content_type="image/jpeg")

    post = await get_post(post_id)
    # Return to original post if no post found
    if not post:
        raise web.HTTPFound(
            f"https://www.instagram.com/p/{post_id}",
        )

    images = []
    async with aiohttp.ClientSession() as session:
        for media in post.medias:
            if media.type == "GraphImage":
                images.append(media.url)

    grid_fname = await grid_sf.do(
        post_id, grid_from_urls, images, f"cache/grid/{post_id}.jpeg"
    )
    if grid_fname is None:
        raise

    with open(grid_fname, "rb") as f:
        return web.Response(body=f.read(), content_type="image/jpeg")


async def init_cache():
    await post_cache.init_cache()
    await shareid_cache.init_cache()


if __name__ == "__main__":
    import asyncio

    import uvloop

    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    asyncio.run(init_cache())

    app = web.Application()
    app.add_routes(
        [
            web.get("/", home),
            web.get("/p/{post_id}", embed),
            web.get("/p/{post_id}/{media_num}", embed),
            web.get("/{username}/p/{post_id}", embed),
            web.get("/{username}/p/{post_id}/{media_num}", embed),
            web.get("/{username}/reel/{post_id}", embed),
            web.get("/tv/{post_id}", embed),
            web.get("/reel/{post_id}", embed),
            web.get("/reels/{post_id}", embed),
            web.get("/stories/{username}/{post_id}", embed),
            web.get("/images/{post_id}/{media_id}", media_redirect),
            web.get("/videos/{post_id}/{media_id}", media_redirect),
            web.get("/grid/{post_id}", grid),
            web.get("/p/{post_id}/", embed),
            web.get("/p/{post_id}/{media_num}/", embed),
            web.get("/{username}/p/{post_id}/", embed),
            web.get("/{username}/p/{post_id}/{media_num}/", embed),
            web.get("/{username}/reel/{post_id}/", embed),
            web.get("/tv/{post_id}/", embed),
            web.get("/reel/{post_id}/", embed),
            web.get("/reels/{post_id}/", embed),
            web.get("/stories/{username}/{post_id}/", embed),
            web.get("/images/{post_id}/{media_id}/", media_redirect),
            web.get("/videos/{post_id}/{media_id}/", media_redirect),
            web.get("/grid/{post_id}/", grid),
        ]
    )
    web.run_app(
        app, host=HOST, port=PORT
    )
