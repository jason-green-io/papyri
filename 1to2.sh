# requires the `rename` command be installed
rename  's/map_(.*)_(.*)_(.*)\.[0-9]*_-1_(.*)_(.*)_(.*)/$1.$2.$3.minecraft\@the_nether.$4.$5.$6/' maps/*
rename  's/map_(.*)_(.*)_(.*)\.[0-9]*_0_(.*)_(.*)_(.*)/$1.$2.$3.minecraft\@overworld.$4.$5.$6/' maps/*
rename  's/map_(.*)_(.*)_(.*)\.[0-9]*_1_(.*)_(.*)_(.*)/$1.$2.$3.minecraft\@the_end.$4.$5.$6/' maps/*

rename  's/merged_map_-1_(.*)_(.*)/minecraft\@the_nether.$1.$2/' merged-maps/*
rename  's/merged_map_0_(.*)_(.*)/minecraft\@overworld.$1.$2/' merged-maps/*
rename  's/merged_map_1_(.*)_(.*)/minecraft\@the_end.$1.$2/' merged-maps/*
