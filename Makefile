.DEFAULT_GOAL := check

src = src
package = radioscripts
pysources = $(wildcard $(src)/$(package)/*.py)
zipapp = dist/$(package).pyz

$(zipapp): $(pysources) # build Python zip archive
	python3 -m zipapp -c -m "$(package).cli:entrypoint" -o $@ $(src)

.PHONY: package
package: # build Python package
	python3 -m build --no-isolation

build: $(zipapp) package

.PHONY: format
format: # format sources with black
	black $(pysources)

.PHONY: lint
lint: # lint codebase with pylint
	pylint $(pysources)

.PHONY: check
check: format lint
