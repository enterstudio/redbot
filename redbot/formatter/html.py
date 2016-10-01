#!/usr/bin/env python

"""
HTML Formatter for REDbot.
"""


from cgi import escape as cgi_escape
import codecs
from functools import partial
import json
import operator
import os
import re
import textwrap
try:
    from urllib.parse import urljoin, quote as urlquote
except ImportError: # python2
    from urlparse import urljoin
    from urllib import quote as urlquote

from markdown import markdown

import thor
import thor.http.error as httperr

from redbot import __version__
from redbot.formatter import Formatter, html_header, relative_time, f_num
from redbot.resource import HttpResource, active_check
from redbot.message.headers import HeaderProcessor
from redbot.speak import levels, categories

nl = "\n"
e_html = partial(cgi_escape, quote=True)

# Configuration; override to change.
static_root = 'static' # where status resources are located
extra_dir = 'extra' # where extra resources are located


class BaseHtmlFormatter(Formatter):
    """
    Base class for HTML formatters."""
    media_type = "text/html"

    def __init__(self, *args, **kw):
        Formatter.__init__(self, *args, **kw)
        self.hidden_text = []
        self.start = thor.time()

    def feed(self, chunk):
        pass

    def start_output(self):
        if self.resource:
            uri = self.resource.request.uri
            req_headers = self.resource.request.headers
        else:
            uri = ""
            req_headers = []
        extra_title = " <span class='save'>"
        if self.kw.get('is_saved', None):
            extra_title += " saved "
        if self.resource and self.resource.check_name != "default":
            extra_title += "%s response" % e_html(self.resource.check_name)
        extra_title += "</span>"
        if self.kw.get('is_blank', None):
            extra_body_class = "blank"
        else:
            extra_body_class = ""
        if self.kw.get('descend', False):
            descend = "&descend=True"
        else:
            descend = ''
        self.output(html_header.__doc__ % {
            'static': static_root,
            'version': __version__,
            'html_uri': e_html(uri),
            'js_uri': e_js(uri),
            'js_req_hdrs': ", ".join(['["%s", "%s"]' % (
                e_js(n), e_js(v)) for n, v in req_headers]),
            'config': json.dumps({
                'redbot_uri': uri,
                'redbot_req_hdrs': req_headers,
                'redbot_version': __version__
            }, ensure_ascii=True).replace('<', '\\u003c'),
            'extra_js': self.format_extra('.js'),
            'test_id': self.kw.get('test_id', ""),
            'extra_title': extra_title,
            'extra_body_class': extra_body_class,
            'descend': descend
        })

    def finish_output(self):
        """
        The bottom bits.
        """
        self.output(self.format_extra())
        self.output(self.format_footer())
        self.output("</body></html>\n")

    def error_output(self, message):
        """
        Something bad happend.
        """
        self.output("<p class='error'>%s</p>" % message)

    def status(self, message):
        "Update the status bar of the browser"
        self.output("""
<script>
<!-- %3.3f
$('#red_status').text("%s");
-->
</script>
""" % (thor.time() - self.start, e_html(message)))

    def final_status(self):
#        See issue #51
#        self.status("RED made %(reqs)s requests in %(elapse)2.3f seconds." % {
#            'reqs': fetch.total_requests,
        self.status("RED finished in %(elapse)2.3f seconds." % {
            'elapse': thor.time() - self.start})

    def format_extra(self, etype='.html'):
        """
        Show extra content from the extra_dir, if any. MUST be UTF-8.
        Type controls the extension included; currently supported:
          - '.html': shown only on start page, after input block
          - '.js': javascript block (with script tag surrounding)
            included on every page view.
        """
        o = []
        if extra_dir and os.path.isdir(extra_dir):
            extra_files = [p for p in os.listdir(extra_dir) if os.path.splitext(p)[1] == etype]
            for extra_file in extra_files:
                extra_path = os.path.join(extra_dir, extra_file)
                try:
                    o.append(codecs.open(
                        extra_path, mode='r', encoding='utf-8', errors='replace').read())
                except IOError as why:
                    o.append("<!-- error opening %s: %s -->" % (extra_file, why))
        return nl.join(o)

    def format_hidden_list(self):
        "return a list of hidden items to be used by the UI"
        return "<ul>" + "\n".join(["<li id='%s'>%s</li>" % (lid, text) for \
            (lid, text) in self.hidden_text]) + "</ul>"

    def format_footer(self):
        "page footer"
        return """\
<br />
<div class="footer">
<p class="navigation">
<a href="https://REDbot.org/about/">about</a> |
<script type="text/javascript">
   document.write('<a href="#help" id="help"><strong>help</strong></a> |')
</script>
<a href="https://REDbot.org/project">project</a> |
<a href="https://twitter.com/redbotorg"><img class="twitterlogo" src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAcCAYAAAAAwr0iAAACzElEQVR4Ae1VRbQTMRTFdcUGnUlxd3d3d4clGxzWuLPEnUla3N1hhfsK3+BOJ6lbyJvJKflYfmeH5Jx78n7bf+97Ny8vBf6vv2ft5YULXOJFCsx3UCjvl7ygd1Ld4oIcBH+dUCG9kE4A8JOlfm747eqGFRxmkHBftCNYRv1ZxY28VM66zTbyoqafdlAr+pW4ie3VJqZptDvNASL+gCx7oknCzUW8AQVYXYVDW3EhJ2vyGZmYRUxCZ6tJZS2VO8LBlZWPcG4SBsIpE7MU2pngKBAViMDnuwwcapg/cYf4UhHYzEC4BZBCRYZFN5Yjb0vnSUTa7iYZ4gamSZGAEKQZAYgzkBAi9CGygiOVpHUJSAd2RUzTssOmP8J9+0SFFn2GLDZJPV/fNtoW7YhzsB+EIQGJbIz8oYku73wpnoMLCNOVjjimUbDVtxdi9gYRtt+w7GnCocVQvSoqAccA+8us9Xv3Onu+Hai8/UtlA7MpguQp2hEDsgQQQ8W+/Zz7DnCOdqXyCqsJ7ErC/tjY+6JkljeXu18J05qyqWLC/rRLbHM3ZpCMAEupwgqSjluEnc0OIkCuA0j0wPoqJ/jPLNaAJcAlg7C5Dh8MpJyWtMvYy0siyw4IwqhsMl0SaqIZH/7SRH//tS7QgcKJW85xADnRJhGHxoVGVbvfewLb7dFA6DYV01WfMv1hp3pksXq66vXHIM8OkdAEGK/QXALpX4nDAHJuB7an687e29uA6TYYTFChhIxZHOYBiBuYLv/2VgA8rio7Q+UqBSKGj0SrIBIcIYQOiAoZXD05dl0Q5kxK+RbMUh8rz8+vnANtBOFhqBCuIgCE0O4UR3syEDuQzXkAHhzd853Dcgmqn+TFxSzvYRJ7kRA5InBTOHAfYXpF7HvgpTS2hxoofVNEb3uOTug/lw2r6XbvSUBV0M0QfyfaGT73LuzhWLiCv2X9X18B0u/OW4cIaXcAAAAASUVORK5CYII="/></a> |
<span class="help">Drag the bookmarklet to your bookmark bar - it makes
checking easy!</span>
<a href="javascript:location%%20=%%20'%(baseuri)s?uri='+encodeURIComponent(location);%%20void%%200"
title="drag me to your toolbar to use RED any time.">REDbot</a> bookmarklet
</p>
</div>

""" % {'baseuri': e_html(self.ui_uri), 'version': __version__}

    def req_qs(self, link=None, check_name=None, res_format=None, use_stored=True, referer=True):
        """
        Format a query string to refer to another RED resource.

        "link" is the resource to test; it is evaluated relative to the current context
        If blank, it is the same resource.

        "check_name" is the request type to show; see active_check/__init__.py. If not specified,
        that of the current context will be used.

        "res_format" is the response format; see formatter/*.py. If not specified, HTML will be
        used.

        If "use_stored" is true, we'll refer to the test_id, rather than make a new request.

        If 'referer" is true, we'll strip any existing Referer and add our own.

        Request headers are copied over from the current context.
        """
        out = []
        uri = self.resource.request.uri
        if use_stored and self.kw.get('test_id', None):
            out.append("id=%s" % e_query_arg(self.kw['test_id']))
        else:
            out.append("uri=%s" % e_query_arg(urljoin(uri, link or "")))
        if self.resource.request.headers:
            for k, v in self.resource.request.headers:
                if referer and k.lower() == 'referer':
                    continue
                out.append("req_hdr=%s%%3A%s" % (e_query_arg(k), e_query_arg(v)))
        if referer:
            out.append("req_hdr=Referer%%3A%s" % e_query_arg(uri))
        if check_name:
            out.append("check_name=%s" % e_query_arg(check_name))
        elif self.resource.check_name != None:
            out.append("check_name=%s" % e_query_arg(self.resource.check_name))
        if res_format:
            out.append("format=%s" % e_query_arg(res_format))
        return "&".join(out)


class SingleEntryHtmlFormatter(BaseHtmlFormatter):
    """
    Present a single RED response in detail.
    """
    # the order of note categories to display
    note_categories = [
        categories.GENERAL,
        categories.SECURITY,
        categories.CONNECTION,
        categories.CONNEG,
        categories.CACHING,
        categories.VALIDATION,
        categories.RANGE]

    # associating categories with subrequests
    note_responses = {
        categories.CONNEG: [active_check.ConnegCheck.check_name],
        categories.VALIDATION: [active_check.ETagValidate.check_name,
                                active_check.LmValidate.check_name],
        categories.RANGE: [active_check.RangeRequest.check_name]}

    # Media types that browsers can view natively
    viewable_types = [
        'text/plain',
        'text/html',
        'application/xhtml+xml',
        'application/pdf',
        'image/gif',
        'image/jpeg',
        'image/jpg',
        'image/png',
        'application/javascript',
        'application/x-javascript',
        'text/javascript',
        'text/x-javascript',
        'text/css']

    # Validator uris, by media type
    validators = {
        'text/html': "http://validator.w3.org/check?uri=%s",
        'text/css': "http://jigsaw.w3.org/css-validator/validator?uri=%s&",
        'application/xhtml+xml': "http://validator.w3.org/check?uri=%s",
        'application/atom+xml': "http://feedvalidator.org/check.cgi?url=%s",
        'application/rss+xml': "http://feedvalidator.org/check.cgi?url=%s"}

    # HTML template for the main response body
    template = """\
    <div id="left_column">
    <span class="help">These are the response headers; hover over each one
    for an explanation of what it does.</span>
    <pre id='response'>%(response)s</pre>

    <p class="options">
        <span class='help'>Here, you can see the response body, a HAR document for the request, and
        when appropriate, validate the response or check its assets (such as referenced images,
        stylesheets and scripts).</span>
        %(options)s
    </p>
    </div>

    <div id="right_column">
    <div id='details'>
    <span class='help right'>These notes explain what REDbot has found
    about your URL; hover over each one for a detailed explanation.</span>
    %(notes)s
    </div>
    <span class="help">If something doesn't seem right, feel free to <a
    href="https://github.com/mnot/redbot/issues/new">file an issue</a>!</span>
    </div>

    <br />

    <div id='body'>
    %(body)s
    </div>

    %(footer)s

    <div class='hidden' id='hidden_list'>%(hidden_list)s</div>
    </body></html>
    """

    name = "html"

    def __init__(self, *args, **kw):
        BaseHtmlFormatter.__init__(self, *args, **kw)

    def finish_output(self):
        self.final_status()
        if self.resource.response.complete:
            self.header_presenter = HeaderPresenter(self)
            self.output(self.template % {
                'response': self.format_response(self.resource),
                'options': self.format_options(self.resource),
                'notes': nl.join([self.format_category(cat, self.resource) \
                    for cat in self.note_categories]),
                'body': self.format_body_sample(self.resource),
                'footer': self.format_footer(),
                'hidden_list': self.format_hidden_list()})
        else:
            if self.resource.response.http_error is None:
                pass # usually a global timeout...
            elif isinstance(self.resource.response.http_error, httperr.HttpError):
                if self.resource.response.http_error.detail:
                    self.error_output("%s (%s)" % (
                        self.resource.response.http_error.desc,
                        self.resource.response.http_error.detail))
                else:
                    self.error_output(self.resource.response.http_error.desc)
            else:
                raise AssertionError("Unknown incomplete response error %s" % \
                                     (self.resource.response.http_error))

    def format_response(self, resource):
        "Return the HTTP response line and headers as HTML"
        offset = 0
        headers = []
        for (name, value) in resource.response.headers:
            offset += 1
            headers.append(self.format_header(name, value, offset))

        return "    <span class='status'>HTTP/%s %s %s</span>\n" % (
            e_html(resource.response.version),
            e_html(resource.response.status_code),
            e_html(resource.response.status_phrase)) + nl.join(headers)

    def format_header(self, name, value, offset):
        "Return an individual HTML header as HTML"
        token_name = "header-%s" % name.lower()
        header_desc = HeaderProcessor.find_header_handler(name).description
        if header_desc and token_name not in [i[0] for i in self.hidden_text]:
            html_desc = markdown(header_desc % {'field_name': name}, output_format="html5")
            self.hidden_text.append((token_name, html_desc))
        return """\
    <span data-offset='%s' data-name='%s' class='hdr'>%s:%s</span>""" % (
        offset,
        e_html(name.lower()),
        e_html(name),
        self.header_presenter.Show(name, value))

    def format_body_sample(self, resource):
        """show the stored body sample"""
        if resource.response.status_code == "206":
            sample = resource.response.payload
        else:
            sample = resource.response.decoded_sample
        try:
            uni_sample = sample.decode(resource.response.character_encoding, "ignore")
        except LookupError:
            uni_sample = sample.decode('utf-8', 'replace')
        safe_sample = e_html(uni_sample)
        message = ""
        if hasattr(resource, "links"):
            for tag, link_set in list(resource.links.items()):
                for link in link_set:
                    try:
                        link = urljoin(resource.response.base_uri, link)
                    except ValueError as why:
                        pass # TODO: pass link problem upstream?
                             # e.g., ValueError("Invalid IPv6 URL")
                    def link_to(matchobj):
                        return r"%s<a href='?%s' class='nocode'>%s</a>%s" % (
                            matchobj.group(1),
                            self.req_qs(link, use_stored=False),
                            e_html(link),
                            matchobj.group(1))
                    safe_sample = re.sub(r"('|&quot;)%s\1" % re.escape(link), link_to, safe_sample)
        if not resource.response.decoded_sample_complete:
            message = "<p class='btw'>RED isn't showing the whole body, because it's so big!</p>"
        return """<pre class="prettyprint">%s</pre>\n%s""" % (safe_sample, message)

    def format_category(self, category, resource):
        """
        For a given category, return all of the non-detail
        notes in it as an HTML list.
        """
        notes = [note for note in resource.notes if note.category == category]
        if not notes:
            return nl
        out = []
        # banner, possibly with links to subreqs
        out.append("<h3>%s\n" % category)
        if isinstance(resource, HttpResource) and category in list(self.note_responses.keys()):
            for check_name in self.note_responses[category]:
                if not resource.subreqs[check_name].fetch_started:
                    continue
                out.append('<span class="req_link"> (<a href="?%s">%s response</a>' % \
                  (self.req_qs(check_name=check_name), check_name))
                smsgs = [note for note in getattr(resource.subreqs[check_name], "notes", []) if \
                  note.level in [levels.BAD]]
                if len(smsgs) == 1:
                    out.append(" - %i warning\n" % len(smsgs))
                elif smsgs:
                    out.append(" - %i warnings\n" % len(smsgs))
                out.append(')</span>\n')
        out.append("</h3>\n")
        out.append("<ul>\n")
        for note in notes:
            out.append("""\
    <li class='%s note' data-subject='%s' data-name='noteid-%s'>
        <span>%s</span>
    </li>""" % (
        note.level,
        e_html(note.subject),
        id(note),
        e_html(note.show_summary(self.lang))))
            self.hidden_text.append(("noteid-%s" % id(note), note.show_text(self.lang)))
        out.append("</ul>\n")
        return nl.join(out)

    def format_options(self, resource):
        "Return things that the user can do with the URI as HTML links"
        options = []
        media_type = resource.response.parsed_headers.get('content-type', [""])[0]
        options.append(
            ("response headers: %s bytes" % f_num(resource.response.header_length),
             "how large the response headers are, including the status line"))
        options.append(("body: %s bytes" % f_num(resource.response.payload_len),
                        "how large the response body is"))
        transfer_overhead = resource.response.transfer_length - resource.response.payload_len
        if transfer_overhead > 0:
            options.append((
                "transfer overhead: %s bytes" % f_num(transfer_overhead),
                "how much using chunked encoding adds to the response size"))
        options.append(None)
        options.append(("""\
<script type="text/javascript">
   document.write("<a href='#' id='body_view' accesskey='b'>view body</a>")
</script>""",
                        "View this response body (with any gzip compression removed)"))
        if isinstance(resource, HttpResource):
            options.append(
                ("""\
        <a href="?%s" accesskey="h">view har</a>""" % self.req_qs(res_format='har'),
                 "View a HAR (HTTP ARchive, a JSON format) file for this test"))
        if not self.kw.get('is_saved', False):
            if self.kw.get('allow_save', False):
                options.append((
                    "<a href=\"#\" id='save' accesskey='s'>save</a>",
                    "Save these results for future reference"))
            if media_type in self.validators:
                options.append((
                    "<a href=\"%s\" accesskey='v'>validate body</a>" %
                    self.validators[media_type] % e_query_arg(resource.request.uri), ""))
            if hasattr(resource, "link_count") and resource.link_count > 0:
                options.append((
                    "<a href=\"?descend=True&%s\" accesskey='a'>" \
                    "check embedded</a>" % self.req_qs(use_stored=False),
                    "run RED on images, frames and embedded links"))
        return nl.join(
            [o and "<span class='option' title='%s'>%s</span>" % (o[1], o[0])
             or "<br>" for o in options])


class HeaderPresenter(object):
    """
    Present a HTTP header in the Web UI. By default, it will:
       - Escape HTML sequences to avoid XSS attacks
       - Wrap long lines
    However if a method is present that corresponds to the header's
    field-name, that method will be run instead to represent the value.
    """

    def __init__(self, formatter):
        self.formatter = formatter

    def Show(self, name, value):
        """
        Return the given header name/value pair after
        presentation processing.
        """
        name = name.lower()
        name_token = name.replace('-', '_')
        if name_token[0] != "_" and hasattr(self, name_token):
            return getattr(self, name_token)(name, value)
        else:
            return self.I(e_html(value), len(name))

    def BARE_URI(self, name, value):
        "Present a bare URI header value"
        value = value.rstrip()
        svalue = value.lstrip()
        space = len(value) - len(svalue)
        return "%s<a href=\"?%s\">%s</a>" % (
            " " * space,
            self.formatter.req_qs(svalue, use_stored=False),
            self.I(e_html(svalue), len(name)))
    content_location = location = x_xrds_location = BARE_URI

    @staticmethod
    def I(value, sub_width):
        "wrap a line to fit in the header box"
        hdr_sz = 75
        sw = hdr_sz - min(hdr_sz-1, sub_width)
        tr = textwrap.TextWrapper(width=sw, subsequent_indent=" "*8, break_long_words=True)
        return tr.fill(value)



class TableHtmlFormatter(BaseHtmlFormatter):
    """
    Present a summary of multiple RED responses.
    """
    # HTML template for the main response body
    template = """\
    <table id='summary'>
    %(table)s
    </table>
    <p class="options">
        %(options)s
    </p>

    <div id='details'>
    %(problems)s
    </div>

    <div class='hidden' id='hidden_list'>%(hidden_list)s</div>

    %(footer)s

    </body></html>
    """
    can_multiple = True
    name = "html"


    def __init__(self, *args, **kw):
        BaseHtmlFormatter.__init__(self, *args, **kw)
        self.problems = []

    def finish_output(self):
        self.final_status()
        self.output(self.template % {
            'table': self.format_tables(self.resource),
            'problems': self.format_problems(),
            'options': self.format_options(self.resource),
            'footer': self.format_footer(),
            'hidden_list': self.format_hidden_list()})

    link_order = [
        ('link', 'Head Links'),
        ('script', 'Script Links'),
        ('frame', 'Frame Links'),
        ('iframe', 'IFrame Links'),
        ('img', 'Image Links')]
    def format_tables(self, resource):
        out = [self.format_table_header()]
        out.append(self.format_droid(resource))
        for hdr_tag, heading in self.link_order:
            droids = [d[0] for d in resource.linked if d[1] == hdr_tag]
            if droids:
                droids.sort(key=operator.attrgetter('response.base_uri'))
                out.append(self.format_table_header(heading + " (%s)" % len(droids)))
                out += [self.format_droid(d) for d in droids]
        return nl.join(out)

    def format_droid(self, resource):
        out = ['<tr class="droid %s">']
        m = 50
        ct = resource.response.parsed_headers.get('content-type', [""])
        if ct[0][:6] == 'image/':
            cl = " class='preview'"
        else:
            cl = ""
        if len(resource.request.uri) > m:
            out.append("""\
    <td class="uri">
        <a href="%s" title="%s"%s>%s<span class="fade1">%s</span><span class="fade2">%s</span><span class="fade3">%s</span>
        </a>
    </td>""" % (
        "?%s" % self.req_qs(resource.request.uri, use_stored=False),
        e_html(resource.request.uri),
        cl,
        e_html(resource.request.uri[:m-2]),
        e_html(resource.request.uri[m-2]),
        e_html(resource.request.uri[m-1]),
        e_html(resource.request.uri[m])))
        else:
            out.append(
                '<td class="uri"><a href="%s" title="%s"%s>%s</a></td>' % (
                    "?%s" % self.req_qs(resource.request.uri, use_stored=False),
                    e_html(resource.request.uri),
                    cl,
                    e_html(resource.request.uri)))
        if resource.response.complete:
            if resource.response.status_code in ['301', '302', '303', '307', '308'] and \
              'location' in resource.response.parsed_headers:
                out.append(
                    '<td><a href="?descend=True&%s">%s</a></td>' % (
                        self.req_qs(resource.response.parsed_headers['location'], use_stored=False),
                        resource.response.status_code))
            elif resource.response.status_code in ['400', '404', '410']:
                out.append('<td class="bad">%s</td>' % (
                    resource.response.status_code))
            else:
                out.append('<td>%s</td>' % resource.response.status_code)
    # pconn
            out.append(self.format_size(resource.response.payload_len))
            out.append(self.format_yes_no(resource.response.store_shared))
            out.append(self.format_yes_no(resource.response.store_private))
            out.append(self.format_time(resource.response.age))
            out.append(self.format_time(resource.response.freshness_lifetime))
            out.append(self.format_yes_no(resource.ims_support))
            out.append(self.format_yes_no(resource.inm_support))
            if resource.gzip_support:
                out.append("<td>%s%%</td>" % resource.gzip_savings)
            else:
                out.append(self.format_yes_no(resource.gzip_support))
            out.append(self.format_yes_no(resource.partial_support))
            problems = [m for m in resource.notes if \
                m.level in [levels.WARN, levels.BAD]]
            out.append("<td>")
            pr_enum = []
            for problem in problems:
                if problem not in self.problems:
                    self.problems.append(problem)
                pr_enum.append(self.problems.index(problem))
            # add the problem number to the <tr> so we can highlight
            out[0] = out[0] % " ".join(["%d" % p for p in pr_enum])
            # append the actual problem numbers to the final <td>
            for p in pr_enum:
                m = self.problems[p]
                out.append("<span class='prob_num'>" \
                           " %s <span class='hidden'>%s</span></span>" % (
                               p + 1, e_html(m.show_summary(self.lang))))
        else:
            if resource.response.http_error is None:
                err = "response incomplete"
            else:
                err = resource.response.http_error.desc or 'unknown problem'
            out.append('<td colspan="11">%s' % err)
        out.append("</td>")
        out.append('</tr>')
        return nl.join(out)

    def format_table_header(self, heading=None):
        return """
        <tr>
        <th title="The URI tested. Click to run a detailed analysis.">%s</th>
        <th title="The HTTP status code returned.">status</th>
        <th title="The size of the response body, in bytes.">size</th>
        <th title="Whether a shared (e.g., proxy) cache can store the
          response.">shared</th>
        <th title="Whether a private (e.g., browser) cache can store the
          response.">private</th>
        <th title="How long the response had been cached before RED got
          it.">age</th>
        <th title="How long a cache can treat the response as
          fresh.">freshness</th>
        <th title="Whether If-Modified-Since validation is supported, using
          Last-Modified.">IMS</th>
        <th title="Whether If-None-Match validation is supported, using
          ETags.">INM</th>
        <th title="Whether negotiation for gzip compression is supported; if
          so, the percent of the original size saved.">gzip</th>
        <th title="Whether partial responses are supported.">partial</th>
        <th title="Issues encountered.">notes</th>
        </tr>
        """ % (heading or "URI")

    def format_time(self, value):
        if value is None:
            return '<td>-</td>'
        else:
            return '<td>%s</td>' % relative_time(value, 0, 0)

    def format_size(self, value):
        if value is None:
            return '<td>-</td>'
        else:
            return '<td>%s</td>' % f_num(value, by1024=True)

    def format_yes_no(self, value):
        icon_tpl = '<td><img src="%s/icon/%%s" alt="%%s"/></td>' % \
            static_root
        if value is True:
            return icon_tpl % ("accept1.png", "yes")
        elif value is False:
            return icon_tpl % ("remove-16.png", "no")
        elif value is None:
            return icon_tpl % ("help1.png", "unknown")
        else:
            raise AssertionError('unknown value')

    def format_options(self, resource):
        "Return things that the user can do with the URI as HTML links"
        options = []
        media_type = resource.response.parsed_headers.get('content-type', [""])[0]
        options.append((
            "<a href='?descend=True&%s'>view har</a>" % self.req_qs(res_format="har"),
            "View a HAR (HTTP ARchive) file for this response"))
        if not self.kw.get('is_saved', False):
            if self.kw.get('allow_save', False):
                options.append((
                    "<a href='#' id='save'>save</a>",
                    "Save these results for future reference"))
        return nl.join(
            [o and "<span class='option' title='%s'>%s</span>" % (o[1], o[0])
             or "<br>" for o in options])

    def format_problems(self):
        out = ['<br /><h2>Notes</h2><ol>']
        for m in self.problems:
            out.append("""\
    <li class='%s %s note' name='msgid-%s'><span>%s</span></li>""" % (
        m.level,
        e_html(m.subject),
        id(m),
        e_html(m.show_summary(self.lang))))
            self.hidden_text.append(("msgid-%s" % id(m), m.show_text(self.lang)))
        out.append("</ol>\n")
        return nl.join(out)


# Escaping functions.
uri_gen_delims = r":/?#[]@"
uri_sub_delims = r"!$&'()*+,;="
def unicode_url_escape(url, safe):
    """
    URL escape a unicode string. Assume that anything already encoded
    is to be left alone.
    """
    # also include "~" because it doesn't need to be encoded,
    # but Python does anyway :/
    return urlquote(url, safe + r'%~')
e_url = partial(unicode_url_escape, safe=uri_gen_delims + uri_sub_delims)
e_authority = partial(unicode_url_escape, safe=uri_sub_delims + r"[]:@")
e_path = partial(unicode_url_escape, safe=uri_sub_delims + r":@/")
e_path_seg = partial(unicode_url_escape, safe=uri_sub_delims + r":@")
e_query = partial(unicode_url_escape, safe=uri_sub_delims + r":@/?")
e_query_arg = partial(unicode_url_escape, safe=r"!$'()*+,:@/?")
e_fragment = partial(unicode_url_escape, safe=r"!$&'()*+,;:@=/?")

def e_js(instr):
    """
    Make sure instr is safe for writing into a double-quoted
    JavaScript string.
    """
    if not instr:
        return ""
    instr = instr.replace('\\', '\\\\')
    instr = instr.replace('"', r'\"')
    instr = instr.replace('<', r'\x3c')
    return instr
