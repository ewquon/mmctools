import re

class InputFile(object):
    """Object to parse and store openfoam input file data
    
    Based on NWTC/datatools.openfoam_util.read_all_defs()
    """
    DEBUG = False

    block_defs = [
        ('{','}',dict),
        ('(',')',list),
    ]
    true_values = [
        'true','t',
        'on',
        'yes','y',
    ]
    false_values = [
        'false','f',
        'off',
        'no','n',
        'none',
    ]


    def __init__(self,fpath):
        self._properties = {}
        # read full file
        with open(fpath) as f:
            lines = f.readlines()
        # trim single-line comments and remove directives
        for i,line in enumerate(lines):
            line = line.strip()
            if line.startswith('#'):
                if self.DEBUG:
                    print('Ignoring directive:',line)
                lines[i] = ''
            else:
                idx = line.find('//')
                if idx >= 0:
                    lines[i] = line[:idx].strip()
        # trim multi-line comments
        txt = '\n'.join(lines)
        idx0 = txt.find('/*')
        while idx0 >= 0:
            idx1 = txt.find('*/',idx0+1)
            assert (idx1 > idx0), 'Mismatched comment block'
            if self.DEBUG:
                print('Remove comment block:',txt[idx0:idx1])
            txt = txt[:idx0] + txt[idx1+2:]
            idx0 = txt.find('/*')
        # consolidate definitions into single lines
        txt = txt.replace('\n',' ')
        txt = txt.replace('\t',' ')
        txt = txt.strip()
        for name,line,containertype in self._split_defs(txt):
            if self.DEBUG:
                print('PARSING',name,'FROM',line,'of TYPE',containertype)
            self._parse(name,line,containertype)

    def __repr__(self):
        descstrs = [
            '{:s} : {:s}'.format(key,str(val))
            for key,val in self._properties.items()
        ]
        return '\n'.join(descstrs)

    def _split_defs(self,txt):
        """Splits blocks of text into lines in the following forms:
            key value;
            key (values...)
            key {values...}
            (values...)
            ((values...) (values...))
        where lists and dicts may be nested. The outlier case is the
        (nested) list which takes on the key of its parent.
        """
        names, lines, container = [], [], []
        while len(txt) > 0:
            if (txt[0] == '('):
                # special treatment for lists, or lists within a list
                name = None
            else:
                # - find first word (name)
                idx = txt.find(' ')
                name = txt[:idx]
                if self.DEBUG: print('name=',name)
                txt = txt[idx+1:].strip()
            # - find next word (either a value/block)
            idx = txt.find(' ')
            if idx < 0:
                # EOF
                string = txt
                txt = '' # to exit loop
                if self.DEBUG: print('EOF',string)
            else:
                string = txt[:idx].strip()
            if string.endswith(';'):
                # found single definition
                if self.DEBUG: print('value=',string[:-1])
                names.append(name)
                lines.append(string[:-1]) # strip ;
                container.append(None)
            else:
                # found block
                blockstart = string[0]
                blockend = None
                blocktype = None
                for block in self.block_defs:
                    if blockstart == block[0]:
                        blockend = block[1]
                        blocktype = block[2]
                        break
                assert (blockend is not None), 'Unknown input block '+blockstart
                # find end of block
                idx = txt.find(blockend) + 1
                assert (idx > 0), 'Mismatched input block'
                blockdef = re.sub(' +',' ',txt[:idx].strip())
                Nopen = blockdef.count(blockstart)
                Nclose = blockdef.count(blockend)
                while Nopen != Nclose:
                    if self.DEBUG:
                        print('  incomplete:',blockdef)
                    idx = txt.find(blockend, idx+1) + 1
                    blockdef = txt[:idx].strip()
                    Nopen = blockdef.count(blockstart)
                    Nclose = blockdef.count(blockend)
                # select block
                if self.DEBUG: print('complete block=',blockdef)
                names.append(name)
                lines.append(blockdef)
                container.append(blocktype)
            if self.DEBUG: print('container type=',container[-1])
            # trim text block
            txt = txt[idx+1:].strip()
        return zip(names, lines, container)

    def _parse(self,name,defn,containertype,parent=None):
        """Parse values split up by _split_defs()

        Casts to float and bool (the latter by checking against a list
        of known true/false values, since bool(some_str) will return 
        True if the string has a nonzero length) will be attempted.

        If the value is a container (i.e., list or dict), then 
        _split_defs() and _parse() will be called recursively.
        """
        if self.DEBUG:
            print('----------- parsing block -----------')
            if parent is not None:
                print('name:',name,'parent:',str(parent))
            if containertype is not None:
                print('container type:',containertype)
        defn = defn.strip()
        if containertype is None:
            # set single value in parent 
            assert(defn.find(' ') < 0)
            try:
                # attempt float cast
                defn = float(defn)
            except ValueError:
                # THIS IS A TRAP
                #try:
                #    # attempt boolean cast
                #    defn = bool(defn)
                #except ValueError:
                #    # default to string
                #    pass
                if defn.lower() in self.true_values:
                    defn = True
                elif defn.lower() in self.false_values:
                    defn = False
                else:
                    # default to string
                    defn = defn.strip('"')
                    defn = defn.strip('\'')
            # SET VALUE HERE
            if self.DEBUG:
                print(name,'-->',defn)
            if parent is None:
                self._properties[name] = defn
            elif isinstance(parent, dict):
                parent[name] = defn
            else:
                parent.append(defn)
        else:
            # we have a subblock, create new container
            if parent is None:
                # parent is the InputFile object
                self._properties[name] = containertype()
                newparent = self._properties[name]
            elif isinstance(parent, dict):
                # parent is a dictionary
                if self.DEBUG:
                    print('add dictionary entry,',name)
                parent[name] = containertype()
                newparent = parent[name]
            else:
                if self.DEBUG:
                    print('add list item,',name)
                # parent is a list
                newparent = containertype()
                parent.append(newparent)
            newdefn = defn[1:-1].strip()
            if (containertype is list) \
                    and ('(' not in newdefn) and (')' not in newdefn):
                # special treatment for lists
                for val in newdefn.split():
                    # recursively call parse wihout a name (None for
                    # list) and without a container type to indicate
                    # that a new value should be set
                    self._parse(None,val,None,parent=newparent)
            else:
                for newname,newdef,newcontainertype in self._split_defs(newdefn):
                    self._parse(newname,newdef,newcontainertype,parent=newparent)

    """
    dictionary-like functions
    """
    def __getitem__(self, key):
        return self._properties[key]

    def keys(self):
        return self._properties.keys()

    def items(self):
        return self._properties.items()

