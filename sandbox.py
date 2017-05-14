from classLibCurrent import *


a = [1,3,2]
print(len(a))
for _ in range(10):
    print(rng.randint(0, len(a)-rngoffset))

b = a.copy()

a[1] = 'derp'
print(a)
print(b)
