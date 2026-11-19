# Demo site for the flow validator samples. Nothing here runs in a test.
BUCKET := s3://demo-site-example-bucket
URL    := https://demo-site.example.com/

# Reads only: lists the pages and counts their links.
lint:
	ls site/*.html
	grep -c '<a href' site/index.html

# Writes: uploads the site to the bucket.
deploy:
	aws s3 sync site/ $(BUCKET) --delete

# Deploys first, then reads the live page.
live-check: deploy
	curl -s $(URL) | grep -c 'class="footer"'

.PHONY: lint deploy live-check
