# Album-MV-merge

将网络下载的MV的垃圾音质替换成flac无损压缩的高音质

## why?

因为有时候闲的没事干只听音乐没感觉，但是看mv的话会感觉音质不行，而如果自己手动进行替换的话可能还会出现音轨没对齐导致音画不同步

所以此仓库中就会自动判断mv和提供的flac文件的音质以及计算并对齐其音轨并通过mkvtool进行封装

## how to use

1. `pip install librosa numpy`
2. 下载MKVToolnix并将mkvmerge放入环境变量（Windows中可以直接放在c盘Windows文件夹中）
3. 修改其main.py中的[此部分](https://github.com/misaka10843/Album-MV-merge/blob/a1ded51b066fdb49387b33cdb37ca0a16f7afca6/main.py#L177C1-L182C6)并运行即可
