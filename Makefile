all: install

install:
	pip3 install -e .

clean:
	pip3 uninstall .
	rm -rf reddit_slurp.egg-info __pycache__
