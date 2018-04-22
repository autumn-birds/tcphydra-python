
class XmlTagOutputter:
    """A small way to easily and quickly generate XML output.
    
    Don't use the escape() routine if you're generating HTML.  (We're not
    generating HTML with this project, at least not directly, so we don't care
    as much about all the attacks you can do against user content injected
    into HTML that gets displayed by a browser.)"""
    def __init__(self, indent='\t'):
        self.indent = indent
        self.indent_level = 0
        self.tag_stack = []
        self.xml = ""
        self.write_callback = None
        self.buffer = True

    def escape(self, txt):
        return txt.replace('<', '&lt;').replace('>', '&gt;') \
                  .replace('&', '&amp;') \
                  .replace('"', '&quot;').replace("'", '&apos;') \
                  .replace('\n', '')

    def write(self, txt):
        """Write a single line of raw text into the document, respecting
        indentation.
        
        Watch out!  You must escape `txt` yourself if it needs to
        be escaped.  This is because this method is designed for adding
        literal code to the document -- for example, a header or something
        with embedded tags."""
        line = "{}{}\n".format(self.indent * self.indent_level, \
                               txt)

        if self.write_callback is not None:
            self.write_callback(line)

        if self.buffer:
            self.xml += line

    def tag_from_spec(self, tag, props):
        """Generate an opening tag with the provided name and properties."""
        assert type(tag) == str

        tag = "<{}".format(tag)

        for k, v in props.items():
            if type(v) == int:
                v = str(v)

            if type(k) != str or type(v) != str:
                raise ValueError("Properties and values must be strings")

            tag += " {}='{}'".format(k, self.escape(v))

        return tag + ">"

    def open_tag(self, tag, props={}):
        """Open a tag."""
        self.write(self.tag_from_spec(tag, props))
        self.indent_level += 1
        self.tag_stack.append(tag)

    def close_tag(self):
        """Close the topmost tag if any is open."""
        if len(self.tag_stack) > 0:
            if self.indent_level > 0:
                self.indent_level -= 1
            self.write("</{}>".format(self.tag_stack.pop()))

    def close_all(self):
        """Close every open tag, effectively finalizing the document."""
        while len(self.tag_stack) > 0:
            self.close_tag()

    def inline_tag(self, tag, props={}, content):
        """Write a self-contained tag on the current line, with content."""
        self.write("{}{}</{}>".format(self.tag_from_spec(tag, props), \
                                      self.escape(content), \
                                      tag))

