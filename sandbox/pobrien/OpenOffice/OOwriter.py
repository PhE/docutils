"""OpenOffice writer

The output is an OpenOffice.org 1.0-compatible document."""

__author__ = "Patrick K. O'Brien <pobrien@orbtech.com>"
__cvsid__ = "$Id$"
__revision__ = "$Revision$"[11:-2]

# Based on work orginally created by:
# Author: Aahz
# Contact: aahz@pythoncraft.com

__docformat__ = 'reStructuredText'

import sys
from warnings import warn
import re

import docutils
from docutils import nodes, utils, writers, languages

import OOtext

import Image  # from the Python Imaging Library

section_styles = [
    '.ch title',
    '.head 1',
    '.head 2',
    '.head 3alone',
    ]


class Writer(writers.Writer):

    supported = ('OpenOffice')
    """Formats this writer supports."""

    output = None
    """Final translated form of `document`."""

    def __init__(self):
        writers.Writer.__init__(self)
        self.translator_class = Translator

    def translate(self):
        visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        self.output = visitor.astext()


class Translator(nodes.NodeVisitor):

    header = [OOtext.content_header]
    footer = [OOtext.content_footer]

    start_para = '\n<text:p text:style-name="%s">\n'
    end_para = '\n</text:p>\n'

    start_charstyle = '<text:span text:style-name="%s">'
    end_charstyle = '</text:span>'

    line_break = '\n<text:line-break/>'
    re_spaces = re.compile('  +')
    spaces = '<text:s text:c="%d"/>'

    re_annotation = re.compile(r'#\d+(?:, #\d+)*$')

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        self.settings = document.settings
        self.body = []
        self.section_level = 0
        self.skip_para_tag = False
        self.para_styles = ['.body']
        self.compact_p = 1
        self.compact_simple = None
        self.context = []
        self.inBulletList = False
        self.inEnumList = False
        self.bodyOne = False

    def astext(self):
        """Return the final formatted document as a string."""
        return ''.join(self.header + self.body + self.footer)

    def encode(self, text):
        """Encode special characters in `text` & return."""
        # @@@ A codec to do these and all other HTML entities would be nice.
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace('"', "&quot;")
        text = text.replace(">", "&gt;")
        return text

    def compress_spaces(self, line):
        while 1:
            match = self.re_spaces.search(line)
            if match:
                start, end = match.span()
                numspaces = end - start
                line = line[:start] + (self.spaces % numspaces) + line[end:]
            else:
                break
        return line

    def fix_annotation(self, line):
        match = self.re_annotation.search(line)
        if match:
            pos = match.start()
            line = line[:pos] + '|' + line[pos:]
        return line

    def visit_Text(self, node):
        self.body.append(self.encode(node.astext()))

    def depart_Text(self, node):
        pass

    def visit_admonition(self, node, name):
        self.skip_para_tag = False
        self.para_styles.append('.CALLOUT')

    def depart_admonition(self):
        self.para_styles.pop()
        self.bodyOne = True

    def visit_attention(self, node):
        self.visit_admonition(node, 'attention')

    def depart_attention(self, node):
        self.depart_admonition()

##     def visit_(self, node):
##         pass

##     def depart_(self, node):
##         pass

    def visit_author(self, node):
        pass

    def depart_author(self, node):
        pass

    def visit_authors(self, node):
        pass

    def depart_authors(self, node):
        pass

    def visit_block_quote(self, node):
        self.skip_para_tag = True
        self.body.append(self.start_para % '.quotes')

    def depart_block_quote(self, node):
        self.body.append(self.end_para)
        self.skip_para_tag = False
        self.bodyOne = True

    def visit_bullet_list(self, node):
        self.inBulletList = True
        self.body.append('\n<text:unordered-list text:style-name="BulletList">\n')

    def depart_bullet_list(self, node):
        self.body.append('</text:unordered-list>\n')
        self.inBulletList = False
        self.bodyOne = True

    def visit_caption(self, node):
        pass

    def depart_caption(self, node):
        pass

    def visit_caution(self, node):
        self.visit_admonition(node, 'caution')

    def depart_caution(self, node):
        self.depart_admonition()

    def visit_citation(self, node):
        self.body.append(self.starttag(node, 'table', CLASS='citation',
                                       frame="void", rules="none"))
        self.footnote_backrefs(node)

    def depart_citation(self, node):
        self.body.append('</td></tr>\n'
                         '</tbody>\n</table>\n')

    def visit_citation_reference(self, node):
        href = ''
        if node.has_key('refid'):
            href = '#' + node['refid']
        elif node.has_key('refname'):
            href = '#' + self.document.nameids[node['refname']]
        self.body.append(self.starttag(node, 'a', '[', href=href,
                                       CLASS='citation-reference'))

    def depart_citation_reference(self, node):
        self.body.append(']</a>')

    def visit_classifier(self, node):
        self.body.append(' <span class="classifier-delimiter">:</span> ')
        self.body.append(self.starttag(node, 'span', '', CLASS='classifier'))

    def depart_classifier(self, node):
        self.body.append('</span>')

    def visit_colspec(self, node):
        self.colspecs.append(node)

    def depart_colspec(self, node):
        pass

    def write_colspecs(self):
        width = 0
        for node in self.colspecs:
            width += node['colwidth']
        for node in self.colspecs:
            colwidth = int(node['colwidth'] * 100.0 / width + 0.5)
            self.body.append(self.emptytag(node, 'col',
                                           colwidth='%i%%' % colwidth))
        self.colspecs = []

    def visit_comment(self, node):
        raise nodes.SkipNode

    def visit_date(self, node):
        pass

    def depart_date(self, node):
        pass

    def visit_decoration(self, node):
        pass

    def depart_decoration(self, node):
        pass

    def visit_definition(self, node):
        self.body.append('</dt>\n')
        self.body.append(self.starttag(node, 'dd', ''))
        if len(node) and isinstance(node[0], nodes.paragraph):
            node[0].set_class('first')

    def depart_definition(self, node):
        self.body.append('</dd>\n')

    def visit_definition_list(self, node):
        print node.astext()
        self.body.append(self.starttag(node, 'dl'))

    def depart_definition_list(self, node):
        self.body.append('</dl>\n')

    def visit_definition_list_item(self, node):
        pass

    def depart_definition_list_item(self, node):
        pass

    def visit_description(self, node):
        self.body.append(self.starttag(node, 'td', ''))
        if len(node) and isinstance(node[0], nodes.paragraph):
            node[0].set_class('first')

    def depart_description(self, node):
        self.body.append('</td>')

    def visit_docinfo(self, node):
        raise nodes.SkipNode

    def depart_docinfo(self, node):
        pass

    def visit_doctest_block(self, node):
        self.visit_literal_block(node)

    def visit_document(self, node):
        pass

    def depart_document(self, node):
        pass

    def visit_emphasis(self, node):
        self.body.append(self.start_charstyle % 'italic')

    def depart_emphasis(self, node):
        self.body.append(self.end_charstyle)

    def visit_entry(self, node):
        if isinstance(node.parent.parent, nodes.thead):
            tagname = 'th'
        else:
            tagname = 'td'
        atts = {}
        if node.has_key('morerows'):
            atts['rowspan'] = node['morerows'] + 1
        if node.has_key('morecols'):
            atts['colspan'] = node['morecols'] + 1
        self.body.append(self.starttag(node, tagname, '', **atts))
        self.context.append('</%s>\n' % tagname.lower())
        if len(node) == 0:              # empty cell
            self.body.append('&nbsp;')
        elif isinstance(node[0], nodes.paragraph):
            node[0].set_class('first')

    def depart_entry(self, node):
        self.body.append(self.context.pop())

    def visit_enumerated_list(self, node):
        self.inEnumList = True
        self.body.append('\n<text:ordered-list text:style-name="NumberedList">\n')

    def depart_enumerated_list(self, node):
        self.body.append('</text:ordered-list>\n')
        self.inEnumList = False
        self.bodyOne = True

    def visit_error(self, node):
        self.visit_admonition(node, 'error')

    def depart_error(self, node):
        self.depart_admonition()

    def visit_field(self, node):
        self.body.append(self.starttag(node, 'tr', '', CLASS='field'))

    def depart_field(self, node):
        self.body.append('</tr>\n')

    def visit_field_body(self, node):
        self.body.append(self.starttag(node, 'td', '', CLASS='field-body'))
        if len(node) and isinstance(node[0], nodes.paragraph):
            node[0].set_class('first')

    def depart_field_body(self, node):
        self.body.append('</td>\n')

    def visit_field_list(self, node):
        self.body.append(self.starttag(node, 'table', frame='void',
                                       rules='none', CLASS='field-list'))
        self.body.append('<col class="field-name" />\n'
                         '<col class="field-body" />\n'
                         '<tbody valign="top">\n')

    def depart_field_list(self, node):
        self.body.append('</tbody>\n</table>\n')

    def visit_field_name(self, node):
        atts = {}
        if self.in_docinfo:
            atts['class'] = 'docinfo-name'
        else:
            atts['class'] = 'field-name'
        if len(node.astext()) > 14:
            atts['colspan'] = 2
            self.context.append('</tr>\n<tr><td>&nbsp;</td>')
        else:
            self.context.append('')
        self.body.append(self.starttag(node, 'th', '', **atts))

    def depart_field_name(self, node):
        self.body.append(':</th>')
        self.body.append(self.context.pop())

    def visit_figure(self, node):
##        self.body.append('\n<text:p text:style-name=".body"/>')
        self.body.append(self.start_para % '.figure')

    def depart_figure(self, node):
        self.body.append(self.end_para)
        self.bodyOne = True

    def visit_footnote(self, node):
        raise nodes.SkipNode

    def footnote_backrefs(self, node):
        warn("footnote backrefs not available")

    def depart_footnote(self, node):
        pass

    def visit_footnote_reference(self, node):
        name = node['refid']
        id = node['id']
        number = node['auto']
        for footnote in self.document.autofootnotes:
            if name == footnote['name']:
                break
        self.body.append('<text:footnote text:id="%s">\n' % id)
        self.body.append('<text:footnote-citation text:string-value="%s"/>\n' % number)
        self.body.append('<text:footnote-body>\n')
        self.body.append(self.start_para % '.body')
        for child in footnote.children:
            if isinstance(child, nodes.paragraph):
                self.body.append(child.astext())
        self.body.append(self.end_para)
        self.body.append('</text:footnote-body>\n')
        self.body.append('</text:footnote>')
        raise nodes.SkipNode

    def depart_footnote_reference(self, node):
        pass

    def visit_generated(self, node):
        pass

    def depart_generated(self, node):
        pass

    def visit_header(self, node):
        self.context.append(len(self.body))

    def depart_header(self, node):
        start = self.context.pop()
        self.body_prefix.append(self.starttag(node, 'div', CLASS='header'))
        self.body_prefix.extend(self.body[start:])
        self.body_prefix.append('<hr />\n</div>\n')
        del self.body[start:]

    def visit_hint(self, node):
        self.visit_admonition(node, 'hint')

    def depart_hint(self, node):
        self.depart_admonition()

    def visit_image(self, node):
        name = str(node.attributes['uri'])
        image = Image.open(name)
        format = image.format
        dpi = 96.0
        width, height = image.size
        width /= dpi
        height /= dpi
        scale = None
        if 'scale' in node.attributes:
            scale = node.attributes['scale']
        if scale is not None:
            factor = scale / 100.0
            width *= factor
            height *= factor
        # Add to our list so that rest2oo.py can create the manifest.
        if format == 'PNG':
            OOtext.pictures.append((name, OOtext.m_png_format % name))
        elif format == 'TIFF':
            OOtext.pictures.append((name, OOtext.m_tif_format % name))
        else:
            print '*** Image type not recognized ***', repr(name)
        #self.body.append('<text:line-break/>\n')
        self.body.append('<draw:image draw:style-name="image"\n')
        self.body.append('draw:name="%s"\n' % name)
        self.body.append('text:anchor-type="char"\n')
        self.body.append('svg:width="%0.2finch"\n' % width)
        self.body.append('svg:height="%0.2finch"\n' % height)
        self.body.append('draw:z-index="0"\n')
        self.body.append('xlink:href="#Pictures/%s"\n' % name)
        self.body.append('xlink:type="simple"\n') 
        self.body.append('xlink:show="embed"\n')
        self.body.append('xlink:actuate="onLoad"/>')
        self.body.append('Figure X.X\n')

    def depart_image(self, node):
        pass

    def visit_important(self, node):
        self.visit_admonition(node, 'important')

    def depart_important(self, node):
        self.depart_admonition()

    def visit_index_entry(self, node):
        index_format = '<text:alphabetical-index-mark text:string-value="%s"/>\n'
        self.body.append(self.start_para % '.body')
        entries = node.astext().split('\n')
        for entry in entries:
            self.body.append(index_format % self.encode(entry))
        self.body.append(self.end_para)
        raise nodes.SkipNode

    def visit_interpreted(self, node):
        # @@@ Incomplete, pending a proper implementation on the
        # Parser/Reader end.
        #self.body.append(node['role'] + ':')
        self.body.append(node.astext())
        raise nodes.SkipNode

    def depart_interpreted(self, node):
        pass

    # Don't need footnote labels/numbers
    def visit_label(self, node):
        print "!"
        raise nodes.SkipNode

    def visit_legend(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='legend'))

    def depart_legend(self, node):
        self.body.append('</div>\n')

    def visit_line_block(self, node):
        self.body.append(self.start_para % '.quotes')
        lines = node.astext()
        lines = lines.split('\n')
        lines = self.line_break.join(lines)
        self.body.append(lines)
        self.body.append(self.end_para)
        raise nodes.SkipNode

    def visit_list_item(self, node):
        self.body.append('<text:list-item>')

    def depart_list_item(self, node):
        self.body.append('</text:list-item>\n')

    def visit_literal(self, node):
        self.body.append(self.start_charstyle % 'code')

    def depart_literal(self, node):
        self.body.append(self.end_charstyle)

    def visit_literal_block(self, node):
        self.body.append(self.start_para % '.code first')
        self.body.append(self.end_para)
        lines = self.encode(node.astext())
        lines = lines.split('\n')
        while lines[-1] == '':
            lines.pop()
        for line in lines:
            self.body.append(self.start_para % '.code')
            line = self.fix_annotation(line)
            line = self.compress_spaces(line)
            self.body.append(line)
            self.body.append(self.end_para)
        self.body.append(self.start_para % '.code last')
        self.body.append(self.end_para)
        self.bodyOne = True
        raise nodes.SkipNode

    def visit_note(self, node):
        self.visit_admonition(node, 'note')

    def depart_note(self, node):
        self.depart_admonition()

    def visit_option(self, node):
        if self.context[-1]:
            self.body.append(', ')

    def depart_option(self, node):
        self.context[-1] += 1

    def visit_option_argument(self, node):
        self.body.append(node.get('delimiter', ' '))
        self.body.append(self.starttag(node, 'var', ''))

    def depart_option_argument(self, node):
        self.body.append('</var>')

    def visit_option_group(self, node):
        atts = {}
        if len(node.astext()) > 14:
            atts['colspan'] = 2
            self.context.append('</tr>\n<tr><td>&nbsp;</td>')
        else:
            self.context.append('')
        self.body.append(self.starttag(node, 'td', **atts))
        self.body.append('<kbd>')
        self.context.append(0)          # count number of options

    def depart_option_group(self, node):
        self.context.pop()
        self.body.append('</kbd></td>\n')
        self.body.append(self.context.pop())

    def visit_option_list(self, node):
        self.body.append(
              self.starttag(node, 'table', CLASS='option-list',
                            frame="void", rules="none"))
        self.body.append('<col class="option" />\n'
                         '<col class="description" />\n'
                         '<tbody valign="top">\n')

    def depart_option_list(self, node):
        self.body.append('</tbody>\n</table>\n')

    def visit_option_list_item(self, node):
        self.body.append(self.starttag(node, 'tr', ''))

    def depart_option_list_item(self, node):
        self.body.append('</tr>\n')

    def visit_option_string(self, node):
        self.body.append(self.starttag(node, 'span', '', CLASS='option'))

    def depart_option_string(self, node):
        self.body.append('</span>')

    def visit_paragraph(self, node):
        style = self.para_styles[-1]
        if self.inBulletList:
            style = '.bullet'
        elif self.inEnumList:
            style = '.numlist'
        elif node.astext().startswith('(annotation)'):
            style = '.code NOTATION'
        elif self.bodyOne or node.astext().startswith('#'):
            if style == '.body':
                style = '.body1'
                self.bodyOne = False
        if not self.skip_para_tag:
            self.body.append(self.start_para % style)

    def depart_paragraph(self, node):
        if not self.skip_para_tag:
            self.body.append(self.end_para)

    def visit_problematic(self, node):
        if node.hasattr('refid'):
            self.body.append('<a href="#%s" name="%s">' % (node['refid'],
                                                           node['id']))
            self.context.append('</a>')
        else:
            self.context.append('')
        self.body.append(self.starttag(node, 'span', '', CLASS='problematic'))

    def depart_problematic(self, node):
        self.body.append('</span>')
        self.body.append(self.context.pop())

    def visit_raw(self, node):
        if node.has_key('format') and node['format'] == 'html':
            self.body.append(node.astext())
        raise nodes.SkipNode

    def visit_reference(self, node):
        pass

    def depart_reference(self, node):
        pass

    def visit_revision(self, node):
        pass

    def depart_revision(self, node):
        pass

    def visit_row(self, node):
        self.body.append(self.starttag(node, 'tr', ''))

    def depart_row(self, node):
        self.body.append('</tr>\n')

    def visit_section(self, node):
        self.section_level += 1
        self.bodyOne = True

    def depart_section(self, node):
        self.section_level -= 1

    def visit_strong(self, node):
        self.body.append('<strong>')

    def depart_strong(self, node):
        self.body.append('</strong>')

    def visit_table(self, node):
        self.body.append(
              self.starttag(node, 'table', CLASS="table",
                            frame='border', rules='all'))

    def depart_table(self, node):
        self.body.append('</table>\n')

    def visit_target(self, node):
        if not (node.has_key('refuri') or node.has_key('refid')
                or node.has_key('refname')):
            self.body.append(self.starttag(node, 'a', '', CLASS='target'))
            self.context.append('</a>')
        else:
            self.context.append('')

    def depart_target(self, node):
        self.body.append(self.context.pop())

    def visit_tbody(self, node):
        self.write_colspecs()
        self.body.append(self.context.pop()) # '</colgroup>\n' or ''
        self.body.append(self.starttag(node, 'tbody', valign='top'))

    def depart_tbody(self, node):
        self.body.append('</tbody>\n')

    def visit_term(self, node):
        self.body.append(self.starttag(node, 'dt', ''))

    def depart_term(self, node):
        """
        Leave the end tag to `self.visit_definition()`, in case there's a
        classifier.
        """
        pass

    def visit_tgroup(self, node):
        # Mozilla needs <colgroup>:
        self.body.append(self.starttag(node, 'colgroup'))
        # Appended by thead or tbody:
        self.context.append('</colgroup>\n')

    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        self.write_colspecs()
        self.body.append(self.context.pop()) # '</colgroup>\n'
        # There may or may not be a <thead>; this is for <tbody> to use:
        self.context.append('')
        self.body.append(self.starttag(node, 'thead', valign='bottom'))

    def depart_thead(self, node):
        self.body.append('</thead>\n')

    def visit_tip(self, node):
        self.visit_admonition(node, 'tip')

    def depart_tip(self, node):
        self.depart_admonition()

    def visit_title(self, node):
        """Only 4 section levels are supported by this writer."""
        title_tag = self.start_para % section_styles[self.section_level]
        self.body.append(title_tag)

    def depart_title(self, node):
        self.body.append(self.end_para)

    def visit_topic(self, node):
        if node.has_key('class') and node['class'] == 'contents':
            raise nodes.SkipNode
        else:
            pass

    def depart_topic(self, node):
        pass

    def visit_warning(self, node):
        self.visit_admonition(node, 'warning')

    def depart_warning(self, node):
        self.depart_admonition()

    def visit_system_message(self, node):
        print node.astext()

    def depart_system_message(self, node):
        pass

    def unknown_visit(self, node):
        print "Failure processing at line", node.line
        print "Failure is", node.astext()
        raise NotImplementedError('visiting unimplemented node type: %s'
                                  % node.__class__.__name__)


"""
<text:p text:style-name="Standard">
<draw:image draw:style-name="fr1"
draw:name="G2: hedgehog2" 
text:anchor-type="as-char"
svg:width="3.2465inch" 
svg:height="1.6681inch" 
draw:z-index="0"
xlink:href="#Pictures/100000000000041D0000021D9EBA28D3.png"
xlink:type="simple" 
xlink:show="embed"
xlink:actuate="onLoad"/>
</text:p>
"""
