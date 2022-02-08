help: 
	# see https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

zipapp: ## build Python zip archive
	python3 -m zipapp -c -m "radioscripts.cli:entrypoint" -o dist/radioscripts.pyz src/

package:  ## build Python package
	python3 -m build --no-isolation

format: ## format sources with black
	black src/radioscripts/

lint: ## lint codebase with flake8
	pylint src/radioscripts/

.PHONY .SILENT: help format lint package zipapp
.DEFAULT_GOAL := help
