INSERT OR IGNORE INTO "CONFIG_RSS_PARSER" ("ID", "NAME", "TYPE", "FORMAT", "PARAMS", "NOTE", "SYSDEF") VALUES ('1', '通用', 'XML', '{
    "list": "/rss/channel/item",
    "item": {
        "title": {
            "path": ".//title/text()"
        },
        "enclosure": {
            "path": ".//enclosure[@type=''application/x-bittorrent'']/@url"
        },
        "link": {
            "path": ".//link/text()"
        },
        "description": {
            "path": ".//description/text()"
        },
        "size": {
            "path": ".//link/@length"
        }
    }
}', '', '', 'Y');
INSERT OR IGNORE INTO "CONFIG_RSS_PARSER" ("ID", "NAME", "TYPE", "FORMAT", "PARAMS", "NOTE", "SYSDEF") VALUES ('2', '蜜柑计划', 'XML', '{
    "list": "/rss/channel/item",
    "item": {
        "title": {
            "path": ".//title/text()"
        },
        "enclosure": {
            "path": ".//enclosure[@type=''application/x-bittorrent'']/@url"
        },
        "link": {
            "path": ".//link/text()"
        },
        "description": {
            "path": ".//description/text()"
        },
        "size": {
            "path": ".//link/@length"
        }
    }
}', '', '', 'Y');
INSERT OR IGNORE INTO "CONFIG_RSS_PARSER" ("ID", "NAME", "TYPE", "FORMAT", "PARAMS", "NOTE", "SYSDEF") VALUES ('3', 'TMDB电影片单', 'JSON', '{
    "list": "$.items",
    "item": {
        "title": {
            "path": "title"
        },
        "year": {
            "path": "release_date"
        },
        "type": {
            "value": "movie"
        }
    }
}', 'api_key={TMDBKEY}&language=zh-CN', '', 'Y');
INSERT OR IGNORE INTO "CONFIG_RSS_PARSER" ("ID", "NAME", "TYPE", "FORMAT", "PARAMS", "NOTE", "SYSDEF") VALUES ('4', 'TMDB电视剧片单', 'JSON', '{
    "list": "$.items",
    "item": {
        "title": {
            "path": "name"
        },
        "year": {
            "path": "first_air_date"
        },
        "type": {
            "value": "tv"
        }
    }
}', 'api_key={TMDBKEY}&language=zh-CN', '', 'Y');