all:
	@if [ ! -x /usr/bin/pdflatex ]; then \
          echo "pdflatex command missing, did you forget to install texlive?"; \
          echo "Run \`make installdependencies\` to do this automatically"; \
          false; \
        fi
	@if [ ! -e /usr/share/texlive/texmf-dist/tex/latex/listingsutf8/listingsutf8.sty ]; then \
          echo "listingsutf8.sty is missing, did you forget to install texlive-listingsutf8?"; \
          echo "Run \`make installdependencies\` to do this automatically"; \
          false; \
        fi
	pdflatex kABI.tex
	pdflatex kABI.tex

clean:
	-rm -rf kABI.aux \
            kABI.log \
            kABI.out \
            kABI.pdf \
            kABI.toc

installdependencies:
	sudo dnf install -y -q texlive texlive-listingsutf8
