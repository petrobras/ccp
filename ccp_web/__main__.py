"""``python -m ccp_web`` and the entry point of the frozen desktop app."""

import multiprocessing

if __name__ == "__main__":
    # ccp worker pools use spawn on Windows; a frozen app must handle the
    # child-process bootstrap before anything else.
    multiprocessing.freeze_support()
    from ccp_web.cli import main

    main()
