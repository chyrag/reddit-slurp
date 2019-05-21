all: install

install:
	pip3 install -e .

uninstall:
	pip3 uninstall reddit-slurp

clean:
	rm -rf reddit_slurp.egg-info __pycache__
