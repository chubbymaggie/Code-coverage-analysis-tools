'''
=========================================================================

    Code coverage analysis tool: 
    This program generates log files in Calltree Profile Format.

    Usage:

        coverage_to_callgraph.py <log_file_path> <thread_id> [options]

    ... where:

        <log_file_path> - Path to the log file, that has been generated by
        Coverager.dll (PIN toolkit instrumentation module).

    Walid options are:

        --modules <module_name> - Collect information only for the specified modules.

        --skip-symbols - Don't use PDB loading and parsing for executable modules.


    Specify "*" as thread ID value to process logs from all available threads.


    Example:

        coverage_parse.py Coverager.log * --modules "ieframe,iexplore"


    Developed by:

    Oleksiuk Dmitry, eSage Lab
    mailto:dmitry@esagelab.com
    http://www.esagelab.com/

=========================================================================
'''

import sys, os, time, re

ver = sys.version[:3]

# load python specified version of symlib module
if ver == "2.5":

    from symlib25 import *

elif ver == "2.6":

    from symlib import *

else:

    print "[!] Only Python 2.5 and 2.6 are supported by symlib module"

# if end

APP_NAME = '''
Code Coverage Analysis Tool for PIN
by Oleksiuk Dmitry, eSage Lab (dmitry@esagelab.com)
'''

m_logfile = None
m_routines_list = {}
m_modules_list = {}
m_modules_to_process = []
m_skip_symbols = False

m_call_tree = {}

def log_write(text):

    global m_logfile

    if m_logfile:

        m_logfile.write(text + "\r\n")

    else:

        print text

# def end  

def read_modules_list(file_name):

    global m_modules_list

    m_modules_list['?'] = { 'path': '?', 'processed_items': 0, \
        'symbols_loaded': False, 'alias': 1, 'alias_accessed': False }

    # open input file
    f = open(file_name)
    content = f.readline()

    # read file contents line by line
    while content != "":
        
        content = content.replace("\n", "")
        entry = content.split(":") 
        
        if len(entry) > 3:
        
            entry[2] = entry[2] + ":" + entry[3]

        if content[:1] != "#" and len(entry) >= 3:

            alias = len(m_modules_list) + 1

            module_name = os.path.basename(entry[2]).lower()
            m_modules_list[module_name] = { 'path': entry[2], 'processed_items': 0, \
                'symbols_loaded': False, 'alias': alias, 'alias_accessed': False }

        # if end

        # read the next line
        content = f.readline()        

    # while end    

    f.close()

# def end    

def parse_symbol(string):

    global m_modules_list, m_modules_to_process, m_skip_symbols

    # parse 'name+offset' string
    info = string.split("+")
    if len(info) >= 2:

        info[1] = int(info[1], 16)
        module_path = info[0].lower()

        if m_modules_list.has_key(module_path):

            m_modules_list[module_path]['processed_items'] += 1            

        # if end        

        skip_module = False

        if len(m_modules_to_process) > 0:

            skip_module = True

            for module_flt in m_modules_to_process:

                if module_path.find(module_flt) >= 0:

                    # don't skip this module
                    skip_module = False

                # if end
            # for end        
        # if end

        if skip_module:

            return False

        if m_skip_symbols:

            return string
                
        if m_modules_list.has_key(module_path):

            module_path = m_modules_list[module_path]['path']

        # if end

        # lookup debug symbol for address
        symbol = bestbyaddr(module_path, info[1])
        if symbol != None:

            addr_s = "%s!%s" % (info[0], symbol[0])

            if symbol[1] > 0:

                addr_s += "+0x%x" % symbol[1]

            return addr_s

        # if end

    elif string[0] == "?" and len(m_modules_to_process) > 0:

        if "?" not in m_modules_to_process:

            return False

    # if end

    return string

# def end    

def load_symbols(module_name):

    global m_routines_list, m_modules_list, m_skip_symbols

    if m_skip_symbols:

        return

    module_name = module_name.lower()
    if not m_modules_list.has_key(module_name):

        # unknown module        
        return

    if m_modules_list[module_name]['symbols_loaded']:

        # symbols allready loaded for this module
        return

    # update names for all available routines from this module
    for rtn_addr in m_routines_list:

        if m_routines_list[rtn_addr]['module'].lower() == module_name:

            rtn_name = parse_symbol(m_routines_list[rtn_addr]['name'])
            if rtn_name != False:

                m_routines_list[rtn_addr]['name'] = rtn_name

        # if end
    # for end

    m_modules_list[module_name]['symbols_loaded'] = True

# def end

def read_routines_list(file_name):

    global m_routines_list

    # open input file
    f = open(file_name)
    content = f.readline()

    print "[+] Parsing routines list, please wait...\n"    

    info_list = []
    i = 0

    # read file contents line by line
    while content != "":
        
        sys.stdout.write(["-", "\\", "|", "/"][i])
        sys.stdout.write("\r")
        i = (i + 1) & 3
        
        content = content.replace("\n", "")        
        entry = content.split(":") 

        if content[:1] != "#" and len(entry) >= 3:

            rtn_addr = int(entry[0], 16) # routinr virtual address            
            rtn_name = entry[1]
            rtn_calls = int(entry[2])            
            rtn_alias = len(m_routines_list) + 1

            rtn_module = "?"
            name = entry[1].split("+") 
            if len(name) == 2:

                rtn_module = name[0]                

            m_routines_list[rtn_addr] = { 'name': rtn_name, \
                'module': rtn_module, 'calls': rtn_calls,   \
                'alias': rtn_alias, 'alias_accessed': False }

        # if end

        # read the next line
        content = f.readline()

    # while end    

    f.close()

# def end

def get_rtn_info(rtn):

    global m_routines_list

    # get function name
    fn_name  = m_routines_list[rtn]['name']
    fn_alias = m_routines_list[rtn]['alias']
    
    if m_routines_list[rtn]['alias_accessed'] == False:

        # return full function name and alias
        m_routines_list[rtn]['alias_accessed'] = True

    else:

        # function name has been allready logged, return only alias
        fn_name = ""

    return (fn_alias, fn_name)

# def end

def get_rtn_module_info(rtn):

    global m_modules_list, m_routines_list

    # get function module information
    ob_name  = m_routines_list[rtn]['module']
    mod_name = ob_name.lower()
    ob_alias = m_modules_list[mod_name]['alias']
    
    if m_modules_list[mod_name]['alias_accessed'] == False:

        # return full module name and alias
        m_modules_list[mod_name]['alias_accessed'] = True

    else:

        # module name has been allready logged, return only alias
        ob_name = ""

    return (ob_alias, ob_name)

# def end

def read_calls_list(file_name):

    global m_call_tree

    # open input file
    f = open(file_name)
    content = f.readline()    

    # read file contents line by line
    while content != "":

        content = content.replace("\n", "")        
        entry = content.split(":") 

        if content[:1] != "#" and len(entry) >= 2:

            rtn_src = int(entry[0], 16)
            rtn_dst = int(entry[1], 16)

            if rtn_src != 0:
            
                if not m_call_tree.has_key(rtn_src):

                    m_call_tree[rtn_src] = {}

                # if end

                if not m_call_tree[rtn_src].has_key(rtn_dst):

                    m_call_tree[rtn_src][rtn_dst] = 0

                # if end

                m_call_tree[rtn_src][rtn_dst] += 1
            
            # if end
        # if end

        # read the next line
        content = f.readline()

    # while end    

    f.close()

# def end

if __name__ == "__main__":

    print APP_NAME

    if len(sys.argv) < 3:

        print "USAGE: coverage_to_callgraph.py <LogFilePath> <thread_id> [options]"
        sys.exit()

    # if end

    try:

        import psyco
        psyco.full()

    except:

        print "[!] Psyco is not available"

    thread_id = sys.argv[2]

    if not thread_id.isdigit() and thread_id != "*":

        print "[!] Error: invalid thread id specified"
        sys.exit(-1)

    # if end

    logfile = "Callgrind.out"

    if thread_id.isdigit():

         logfile += "." + thread_id

    fname = sys.argv[1]
    fname_blocks = fname + ".blocks"
    fname_routines = fname + ".routines"
    fname_modules = fname + ".modules"

    # parse command line arguments
    if len(sys.argv) > 3:
        
        for i in range(3, len(sys.argv)):    
        
            if sys.argv[i] == "--modules" and i < len(sys.argv) - 1:
        
                # filter by module name is specified
                modlist = sys.argv[i + 1].split(",")

                for mod in modlist:

                    mod = mod.lstrip()
                    m_modules_to_process.append(mod.lower())

                    print "Filtering by module name \"%s\"" % (mod)

                # for end

            elif sys.argv[i] == "--skip-symbols":
                
                m_skip_symbols = True

            # if end
        # for end
    # if end

    if not os.path.isfile(fname):

        print "[!] Error while opening input file"
        sys.exit(-1)

    # if end    

    if not os.path.isfile(fname_modules):

        print "[!] Error while opening modules log"
        sys.exit(-1)

    # if end

    input_files = []

    if thread_id.isdigit():

        #
        # process single input file
        #
    
        fname_calls = fname + "." + thread_id

        if not os.path.isfile(fname_calls):

            print "[!] Error while opening calls log"
            sys.exit(-1)

        # if end
        
        input_files.append(fname_calls)

    else:

        #
        # use call tree log files for all threads
        #

        files = os.listdir("./")

        for f in files:

            if re.search(fname + ".\\d+", f):

                input_files.append(f)

        # for end            
    # if end

    print "[+] Input file(s): %s" % (", ".join(input_files))

    if logfile:

        # create output file
        m_logfile = open(logfile, "wb+")
        print "[+] Output file: %s" % (logfile)

    # if end

    exec_time = time.time()

    # read target application modules list
    read_modules_list(fname_modules)

    print "[+] %d modules readed" % (len(m_modules_list))

    # read target application routines list
    read_routines_list(fname_routines)

    print "[+] %d routines readed" % (len(m_routines_list))

    ############

    print "[+] Parsing call tree, please wait...\n"        

    # parse all available input files
    for input_file in input_files:

        read_calls_list(input_file)

    log_write("#")
    log_write("# Generated by Code Coverage Analysis Tool for PIN")
    log_write("#\r\n")

    # write call tree information into the callgrind file
    log_write("events: Ir\r\n")

    # enumerate available functions
    for rtn in m_call_tree:

        if not m_routines_list.has_key(rtn):

            continue

        # load debug symbols for module, that contains this function
        load_symbols(m_routines_list[rtn]['module'])

        log_write("ob=(%d) %s" % get_rtn_module_info(rtn))
        log_write("fn=(%d) %s" % get_rtn_info(rtn))
        log_write("0 1")

        # enumerate calls from current function to the others
        for rtn_dst in m_call_tree[rtn]:

            load_symbols(m_routines_list[rtn_dst]['module'])

            log_write("cob=(%d) %s" % get_rtn_module_info(rtn_dst))
            log_write("cfn=(%d) %s" % get_rtn_info(rtn_dst))
            log_write("calls=%d 0" % (m_call_tree[rtn][rtn_dst]))
            log_write("0 1")

        # for end

        log_write("\r\n")

    # for end    

    ############

    exec_time = int(time.time() - exec_time)

    print "\n[+] DONE (%d mins., %d secs.)\n" % (exec_time / 60, exec_time % 60)

# if end    

#
# EoF
#
