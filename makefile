.PHONY	= help	install-requirements	update-driver

install-requirements:
	pip install -Ur ./app/requirements.txt

update-driver:
	. ./app/update-driver.sh

test:
	cd ./app; python -m unittest

clean:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
