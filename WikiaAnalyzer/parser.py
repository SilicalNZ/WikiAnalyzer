from html.parser import HTMLParser as _HTMLParser


class CloseableList:
    def __init__(self, *args):
        self.n = [*args]
        self.closed = False

    def close(self):
        self.closed = True

    def open(self):
        self.closed = False

    def __setitem__(self, key, value):
        if not self.closed:
            self.n[key] = value

    def __getitem__(self, item):
        return self.n[item]

    def extend(self, item):
        self.n.extend(item)

    def append(self, item):
        if not self.closed:
            self.n.append(item)

    def pop(self, index):
        self.n.pop(index)

    def __repr__(self):
        return repr(self.n)

    def __str__(self):
        return str(self.n)

    def __len__(self):
        return len(self.n)


class PreciseHTMLParser(_HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handlers = ('h2', 'td', 'li', 'p', 'dl')

        self.data = CloseableList()
        self.handle = self.data

    def handle_starttag(self, tag, attrs):
        if tag in self.handlers:
            if self.handle and tag == 'li' and self.handle[-1][0] == 'li': # Merge lists
                self.handle = self.handle[-1]
                self.handle.open()
                self.handle.append(str())
            elif self.handle and tag == 'p' and self.handle[-1][0] == 'p': # Merge paragraphs
                self.handle = self.handle[-1]
                self.handle.open()
                self.handle[-1] += '\n'
            else:
                layer = CloseableList(tag)
                self.handle.append(layer)
                self.handle = layer

        for key, item in attrs:
            if key == 'data-src'\
                    or (key == 'href' and item[:5] == 'https'):
                item = CloseableList('url', item)
                item.close()
                self.handle.append(item)

    def handle_endtag(self, tag):
        if tag in self.handlers:
            if tag == 'td' and isinstance(self.handle[-1], CloseableList):
                new_handle = self.handle[-1]
                [self.handle.pop(x) for x in range(len(self.handle) -1, -1, -1)]
                [self.handle.append(i) for i in new_handle]
            elif tag == 'li':
                try:
                    self.handle[-1] = self.handle[-1].strip()
                except:
                    pass
            self.handle.close()
            self.handle = self.data
            while not self.handle[-1].closed:
                self.handle = self.handle[-1]
            if len(self.handle[-1]) <= 1:  # Remove empty data
                self.handle.pop(-1)

    def handle_data(self, data):
        if data.strip(): # Ignore " "
            if len(self.handle) > 1 and isinstance(self.handle[-1], str):  # Merge strings together
                if self.handle[-1] == ':':
                    self.handle[-1] += ' '
                self.handle[-1] += data
            else:
                self.handle.append(data)

    def feed(self, data):
        data = data.replace('\u200b', '')

        super().feed(data)
        self.data.close()
        result = self.data
        self.data = CloseableList()
        return result


class LazyHTMLParser(_HTMLParser):
    def __init__(self, *args, group_data=True, tidy_tables=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.tags = ('li', 'td')
        self._results = []
        self.data = []

        self.group_data = group_data
        self.tidy_tables = tidy_tables

    def handle_starttag(self, tag, attrs):
        if tag in self.tags:
            if self.data and self.data[0] == 'td':
                self.handle_endtag('td')
            self.data.append(tag)
        if attrs and len(attrs) == 1 and attrs[0][0] == 'href':
            self.data.append(attrs)

    def handle_endtag(self, tag):
        if tag in self.tags:
            if self.data:
                if all(isinstance(i, str) for i in self.data): # Tidy up data
                    data = ''.join(self.data[1:]).strip()
                else: # Cleanup URL
                    data = tuple(filter(lambda i: isinstance(i, list), self.data))[0][0]

                self._results.append((str(self.data[0]), data))
            self.data = []

    def handle_data(self, data):
        if not self.data:
            self.data.append('td')
        self.data.append(data)

    def feed(self, data):
        data = data.replace('<b>', '**')\
                   .replace('</b>', '**')\
                   .replace('<i>', '*')\
                   .replace('</i>', '*')\
                   .replace('<p>', '<td>')\
                   .replace('</p>', '</td>')\
                   .replace('<hr>', '<td>')\
                   .replace('</hr>', '</td>')

        super().feed(data)
        if self.group_data:
            self._merge_results()
        if self.tidy_tables:
            self._tidy_tables()

        results, self._results = self._results, []
        return results

    def _merge_results(self):
        results = []
        for tag, data in self._results:
            if tag == 'td':
                results.append(data)
            elif not isinstance(results[-1], list):
                results.append([data])
            else:
                results[-1].append(data)

        self._results = []
        for i in results:
            if isinstance(i, str) and not i.strip():
                continue
            self._results.append(i)

    def _tidy_tables(self):
        results = []
        titles = iter(reversed(self._results))
        next(titles)
        lists = iter(reversed(self._results))
        for l, title in zip(lists, titles):
            if isinstance(l, str) and results and l in results[-1][0]:
                continue
            elif isinstance(title, list) or isinstance(title, tuple):
                results.append(l)
            else:
                results.append((title, l))
        self._results = tuple(reversed(results))
