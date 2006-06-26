#!/bin/bash
epydoc 		-o doc --name conduit --css white \
		--url http://john.greenbirdsystems.com \
                --inheritance listed \
		--no-frames \
		--verbose \
                conduit
