#!/usr/bin/bash

#0:"Debugging Solution"
#1:"Alternative Solution"
#2:"Question Repost",
#3:"Direct Solution Provided by Asker"
#4:"Related Information (Not Solution)"
#5:"Direct Solution Provided by Non-Asker"
#6:"Validating Solution"
#7:"Outsourcing SO Post"

files=`find ./ -type f | grep .json`

for f in "$files"; do
path=`realpath $f`
category=`cat $path | jq -r '.category' | tr -d '\n'`
count=${counts[$category]}
echo "$count"
#counts[$category] = 1
done
echo "${counts[@]}"
exit 0
