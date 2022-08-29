#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Website property.
"""
try:
    from importlib.resources import files  # @UnresolvedImport
except ImportError:
    from importlib_resources import files  # @UnresolvedImport

from rebulk.remodule import re

from rebulk import Rebulk, Rule, RemoveMatch
from ..common import seps
from ..common.formatters import cleanup
from ..common.pattern import is_disabled
from ..common.validators import seps_surround
from ...reutils import build_or_pattern


def website(config):
    """
    Builder for rebulk object.

    :param config: rule configuration
    :type config: dict
    :return: Created Rebulk object
    :rtype: Rebulk
    """
    rebulk = Rebulk(disabled=lambda context: is_disabled(context, 'website'))
    rebulk = rebulk.regex_defaults(flags=re.IGNORECASE).string_defaults(ignore_case=True)
    rebulk.defaults(name="website")

    tld_file = files('guessit.data').joinpath('tlds-alpha-by-domain.txt').read_text(encoding='utf-8')
    tlds = [
           tld.strip()
           for tld in tld_file.split('\n')
           if '--' not in tld
       ][1:]# All registered domain extension

    safe_tlds = config['safe_tlds']  # For sure a website extension
    safe_subdomains = config['safe_subdomains']  # For sure a website subdomain
    safe_prefix = config['safe_prefixes']  # Those words before a tlds are sure
    website_prefixes = config['prefixes']

    rebulk.regex(r'(?:[^a-z0-9]|^)((?:'+build_or_pattern(safe_subdomains) +
                 r'\.)+(?:[a-z-0-9-]+\.)+(?:'+build_or_pattern(tlds) +
                 r'))(?:[^a-z0-9]|$)',
                 children=True)
    rebulk.regex(r'(?:[^a-z0-9]|^)((?:'+build_or_pattern(safe_subdomains) +
                 r'\.)*[a-z0-9-]+\.(?:'+build_or_pattern(safe_tlds) +
                 r'))(?:[^a-z0-9]|$)',
                 safe_subdomains=safe_subdomains, safe_tlds=safe_tlds, children=True)
    rebulk.regex(r'(?:[^a-z0-9]|^)((?:'+build_or_pattern(safe_subdomains) +
                 r'\.)*[a-z0-9-]+\.(?:'+build_or_pattern(safe_prefix) +
                 r'\.)+(?:'+build_or_pattern(tlds) +
                 r'))(?:[^a-z0-9]|$)',
                 safe_subdomains=safe_subdomains, safe_prefix=safe_prefix, tlds=tlds, children=True)

    rebulk.string(*website_prefixes,
                  validator=seps_surround, private=True, tags=['website.prefix'])

    class PreferTitleOverWebsite(Rule):
        """
        If found match is more likely a title, remove website.
        """
        consequence = RemoveMatch

        @staticmethod
        def valid_followers(match):
            """
            Validator for next website matches
            """
            return match.named('season', 'episode', 'year')

        def when(self, matches, context):
            to_remove = []
            for website_match in matches.named('website'):
                safe = False
                for safe_start in safe_subdomains + safe_prefix:
                    if website_match.value.lower().startswith(safe_start):
                        safe = True
                        break
                if not safe:
                    suffix = matches.next(website_match, PreferTitleOverWebsite.valid_followers, 0)
                    if suffix:
                        group = matches.markers.at_match(website_match, lambda marker: marker.name == 'group', 0)
                        if not group:
                            to_remove.append(website_match)
            return to_remove

    rebulk.rules(PreferTitleOverWebsite, ValidateWebsitePrefix)

    return rebulk


class ValidateWebsitePrefix(Rule):
    """
    Validate website prefixes
    """
    priority = 64
    consequence = RemoveMatch

    def when(self, matches, context):
        to_remove = []
        for prefix in matches.tagged('website.prefix'):
            website_match = matches.next(prefix, predicate=lambda match: match.name == 'website', index=0)
            if (not website_match or
                    matches.holes(prefix.end, website_match.start,
                                  formatter=cleanup, seps=seps, predicate=lambda match: match.value)):
                to_remove.append(prefix)
        return to_remove
