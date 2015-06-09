import sys
import logging
import traceback
from importlib import import_module
from SocketServer import ThreadingMixIn
from SimpleXMLRPCServer import SimpleXMLRPCServer

VERSION = 0.0


class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass


def get_backend(backend_type):
    logging.info('get_backend type %s' % backend_type)
    backend = None
    module, _, class_ = backend_type.rpartition('.')
    print "Importing Module: %s\nClass: %s" % (module, class_)
    try:
        backing_module = import_module(module)
    except ImportError as e:
        print e
        logging.warn(e)
    except Exception as e:
        print e
        print traceback.format_exc()
        raw_input("Waiting")
    else:
        try:
            backend = getattr(backing_module, class_)
        except AttributeError as e:
            logging.error(e)
    finally:
        logging.info('get_backend backing object %s' % backend)
        return backend


def main(addr, port, type_):
    logging.warn('Main, Version: %d' % VERSION)
    logging.info('main creating server on %s:%d' % (addr, port))
    server = ThreadedXMLRPCServer((addr, port), allow_none=True)
    backend_type = get_backend(type_)
    if backend_type:
        logging.info('main registering and server')
        server.register_instance(backend_type())
        server.serve_forever()
    
if __name__ == '__main__':
    if 'debug' in sys.argv:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARN)

    try:
        addr = intern(sys.argv[1])
        port = int(sys.argv[2])
        type_ = intern(sys.argv[3])
    except IndexError:
        logging.info('No or invalid arguments found. Defaulting to defaults')
        addr = intern('0.0.0.0')
        port = 4828
        type_ = intern('servers.vserver.EvalServer')
    except ValueError:
        sys.stderr.write("Invalid port number string: %s\n" % sys.argv[2])
        sys.exit(0)
    
    main(addr, port, type_)
