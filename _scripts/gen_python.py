#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs, os, re, subprocess, sys, yaml

# We don't read the index
IGNORED_FILES = "index.md"

# The class for all reql objects
query = 'rethinkdb.ast.RqlQuery.'

# The python class associated with each type
parents = {
    None: '',
    'r': 'rethinkdb.',
    'sequence': query,
    'query': query,
    'stream': query,
    'grouped_stream': query,
    'singleSelection': query,
    'array': query,
    'number': query,
    'bool': query,
    'value': query,
    'string': query,
    'time': query,
    'any': query,
    'geometry': query,
    'point': query,
    'line': query,
    'polygon': query,
    'connection': 'rethinkdb.net.Connection.',
    'cursor': 'rethinkdb.net.Cursor.',
    'db': 'rethinkdb.ast.DB.',
    'table': 'rethinkdb.ast.Table.',
    'set_loop_type': 'rethinkdb.'
}

# The real python names for names used in the docs
tags = {
    '[] (bracket)': [(query, '__getitem__')],
    'nth, []': [(query, 'nth')],
    'slice, []': [(query, 'slice')],
    '+': [(query, '__add__'), ('rethinkdb.', 'add')],
    '-': [(query, '__sub__'), ('rethinkdb.', 'sub')],
    '*': [(query, '__mul__'), ('rethinkdb.', 'mul')],
    '/': [(query, '__div__'), ('rethinkdb.', 'div')],
    '%': [(query, '__mod__'), ('rethinkdb.', 'mod')],
    '&, and_': [(query, '__and__'), ('rethinkdb.', 'and_')],
    '|, or_': [(query, '__or__'), ('rethinkdb.', 'or_')],
    '==, eq': [(query, '__eq__'), (query, 'eq')],
    '!=, ne': [(query, '__ne__'), (query, 'ne')],
    '<, lt': [(query, '__lt__'), (query, 'lt')],
    '>, gt': [(query, '__gt__'), (query, 'gt')],
    '<=, le': [(query, '__le__'), (query, 'le')],
    '>=, ge': [(query, '__ge__'), (query, 'ge')],
    '~, not_': [(query, '__invert__'), (query, 'not_'), ('rethinkdb.', 'not_')],
    'r': [('', 'rethinkdb')],
    'repl': [('rethinkdb.net.Connection.', 'repl')],
    'count': lambda parent: not parent == 'rethinkdb.' and [(query, 'count')] or [],
    'rethinkdb': [('', 'rethinkdb')],
    'to_json_string, to_json': [(query, 'to_json_string'), (query, 'to_json')],
    'for': [],
    'list': [],
    'set_loop_type': [('rethinkdb.', 'set_loop_type')]
}

# Write the header of the docs.py file
def write_header(file):
    commit = subprocess.Popen(['git', 'log', '-n', '1', '--pretty=format:"%H"'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
    file.write('''# This file was generated by _scripts/gen_python.py from the rethinkdb documentation in http://github.com/rethinkdb/docs
# hash: %s

import rethinkdb

docsSource = [
''' % commit)

def write_footer(file):
    '''write the ending of the file'''
    file.write('''
]

for function, text in docsSource:
	try:
		text = str(text.decode('utf-8'))
	except UnicodeEncodeError:
		pass
	if hasattr(function, "__func__"):
		function.__func__.__doc__ = text
	else:
		function.__doc__ = text
''')

# Browse all the docs
def browse_files(base, result_file):
    subdirlist = []
    # Because we don't read from the json file, that is enough to guarantee an order
    for item in sorted(os.listdir(base)):
        if item[0] != '.' and item not in IGNORED_FILES:
            full_path = os.path.join(base, item)
            if os.path.isfile(full_path):
                add_doc(full_path, result_file)
            else:
                subdirlist.append(full_path)

    for subdir in subdirlist:
        browse_files(subdir, result_file)


# Add docs in result for one file
def add_doc(file_name, result_file):
    limiter_yaml = re.compile('---\s*')
    is_yaml = False
    yaml_header = ""

    parent = ""
    func = ""

    # Reading the JS file to extract the io data
    file_name_js = file_name.replace('python', 'javascript')
    try:
        details_file_js = codecs.open(file_name_js, "r", "utf-8")

        yaml_header_js = ""
        for line in details_file_js:
            if limiter_yaml.match(line) != None:
                # We ignore the yaml header
                if is_yaml == False:
                    is_yaml = True
                else:
                    break
            elif is_yaml == True:
                yaml_header_js += line

        yaml_data_js = yaml.load(yaml_header_js)
 
        parent = parents[yaml_data_js['io'][0][0]]

    except:
        # The file may not exist (for repl for example)
        pass


    # Open the python file
    details_file = codecs.open(file_name, "r", "utf-8")

    # Define some regex that we will use
    ignore_pattern = re.compile("#.*#.*|<img.*/>") # Used to skip the titles like Description, Related commands etc.

    # Used to skip the body (command syntax)
    start_body_pattern = re.compile("{%\s*apibody\s*%}\s*")
    end_body_pattern = re.compile("{%\s*endapibody\s*%}\s*")
    parsing_body = False
    
    # Used to convert relative Markdown links to absolute
    link_match_pattern = re.compile(r'\[(.*?)\]\(/')
    link_replace_pattern = r'[\1](http://rethinkdb.com/'
    
    # Tracking the yaml header, we need it for the command name
    is_yaml = False
    yaml_header_py = ""


    # Track if we are parsing some code
    example_code_start_pattern = re.compile("```py")
    example_code_end_pattern = re.compile("```")
    parsing_example_code = False


    text = ""

    for line in details_file:
        # Ignore titles (h1 tags)
        if ignore_pattern.match(line) != None:
            continue

        if limiter_yaml.match(line) != None:
            # We ignore the yaml header
            if is_yaml == False:
                is_yaml = True
            else:
                yaml_data_py = yaml.load(yaml_header_py)
                name = yaml_data_py["command"]
                is_yaml = False
        elif is_yaml == True:
            yaml_header_py += line
        elif is_yaml == False:
            if start_body_pattern.match(line) != None:
                parsing_body = True
            elif end_body_pattern.match(line) != None:
                parsing_body = False
            elif parsing_body == False:
                if example_code_start_pattern.match(line) != None:
                    parsing_example_code = True
                elif example_code_end_pattern.match(line) != None:
                    parsing_example_code = False
                else:
                    if parsing_example_code == True:
                        text += "    " + line
                    else:
                        line = re.sub(link_match_pattern,
                            link_replace_pattern, line)
                        text += line
            else:
                text += line.replace('&rarr;', '->')
    
    encoded = repr(re.sub("(__Example:__)|(__Example__:)", "*Example*", re.sub("^\n+", "", re.sub("\n{2,}", "\n\n", text))).encode('utf-8'))
    if not encoded.startswith('b'): # append the binary marker for Python3 when generateing from Python2.6
        encoded = 'b' + encoded
    
    # If the command has multiple name, parents
    if name in tags:
        names = tags[name]
        if type(names) == type(lambda x: x):
            names = names(parent)

        for parent, name in names:
            result_file.write("\n\t(" + parent + name + ", " + encoded + '),')
    else: # If the command has just one name and one parent
        assert parent not in (None, ''), 'Missing the parent entry for: %s in %s' % (name, file_name)
        result_file.write("\n\t(" + parent + name + ", " + encoded + '),')

if __name__ == "__main__":
    script_path = os.path.dirname(os.path.realpath(__file__))

    result_file = codecs.open(script_path+"/docs.py", "w", "utf-8")
    
    write_header(result_file)

    browse_files(script_path+"/../api/python/", result_file)
    
    write_footer(result_file)

    result_file.close()
