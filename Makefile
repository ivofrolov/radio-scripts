help: 
	# see https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "%-10s %s\n", $$1, $$2}'

app: ## build executable Python zip archive
	python3 -m zipapp -p "/usr/bin/env python3" -m "radioscripts.cli:entrypoint" -o dist/radioscripts src/

format: ## format sources with black
	black src/radioscripts/

lint:  ## lint codebase with flake8
	pylint src/radioscripts/

.PHONY .SILENT: help app format lint
.DEFAULT_GOAL := help
