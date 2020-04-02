if __name__ == '__main__':
    import argparse
    from .shell import AdminShell

    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--file', action='store', help='execute commands from file')

    args = parser.parse_args()

    shell = AdminShell()

    if args.file:
        shell.on_cmdloop_begin()
        with open(args.file, 'r') as fp:
            shell.include(fp)
    else:
        shell.cmdloop()
