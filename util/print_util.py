import sklearn
print(sklearn.__version__)


def pp(*obj):
    print(*obj)
    pl(80)


def up(n):
    print('\n' * n)


def pt(args):
    print(type(*args))
    pl(80)


def pl(n):
    print('-' * n)