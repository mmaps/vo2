import sys


class GuestPool(object):

    def __init__(self, vm_map):
        self.pool = vm_map
        self.ready = dict(zip(vm_map.keys(), [True for i in vm_map]))

    def acquire(self, name):
        rv = None
        if self.ready.get(name):
            self.ready[name] = False
            rv = self.pool.get(name)
        return rv

    def release(self, name):
        if name in self.ready:
            self.ready[name] = True
        else:
            sys.stderr.write("Attempt to release unknown VM: %s\n" % name)

    def __str__(self):
        guests = ['Guest Pool']
        guests.extend(['%s: Ready == %s' % (vm, self.ready.get(vm)) for vm in self.pool])
        return '\n'.join(guests)


if __name__ == '__main__':
    d2 = {'vm1':'a', 'vm2':'b'}
    pool = GuestPool(d2)
    print pool

    poss = ['vm1', 'vm2']
    print 'Acquire 2'
    for i in range(2):
        print pool.acquire(poss)
    pool.release('vm1')
    print 'Released 1'
    print 'Acquire 2'
    for i in range(2):
        print pool.acquire(poss)

    print 'Wait on 1 for 5'
    print pool.acquire(['vm2'], block=True, timeout=5)
