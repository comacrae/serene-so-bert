#!/usr/bin/sh

files=`find . | grep .xml.out`
for f in $files; do
	lc=`wc -l "$f"`
	output=`grep stackoverflow.com "$f" | wc -l`
	echo "$output $lc\n" >> output.txt
	
done
exit 0;
