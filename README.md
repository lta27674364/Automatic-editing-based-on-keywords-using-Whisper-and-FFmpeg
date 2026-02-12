
**[项目作用]**<br>
&emsp;1、当视频演讲者说出特定关键词时会触发剪辑，例如：<br>
  &emsp;设“重来”为关键词，则：<br>
  &emsp;&emsp;“大家好今天说一个扎心的事，说错了，**重来**。大家好...”<br>
  &emsp;会触发剪辑，变成：<br>
  &emsp;&emsp;“大家好...”<br>
&emsp;2、项目会区分识别到的关键词到底是“剪辑指令”还是“演讲内容”，只对“剪辑指令”触发剪辑；<br>

**[如何启动]**<br>
&emsp;1、安装库<br>
&emsp;&emsp;&emsp;```pip install pymysql minio openai moviepy```<br>
&emsp;2、在edit_video1.py配置FFmpeg路径<br>
&emsp;3、在edit_video1.py配置输入视频的路径<br>
&emsp;4、在extract_audio_timestamps.py配置whisper的api和api来源网址，本项目使用了OpenAI客户端<br>
&emsp;5、启动docker，启动mysql，启动minio，启动程序<br>
&emsp;&emsp;启动docker后在项目所在路径的终端输入：<br>
&emsp;&emsp;&emsp;启动mysql<br>
&emsp;&emsp;&emsp;&emsp;```docker run -d --name mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=root123 mysql:8.0```<br>
&emsp;&emsp;&emsp;启动minio<br>
&emsp;&emsp;&emsp;&emsp;```docker run -d --name minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=admin -e MINIO_ROOT_PASSWORD=admin123 minio/minio server /data --console-address ":9001"```<br>
&emsp;&emsp;&emsp;创建数据库<br>
&emsp;&emsp;&emsp;&emsp;```docker exec -it mysql mysql -uroot -proot123 -e "CREATE DATABASE IF NOT EXISTS video_processing;"```<br>
&emsp;&emsp;&emsp;启动程序<br>
&emsp;&emsp;&emsp;&emsp;```python app/main.py```<br>
&emsp;&emsp;&emsp;MinIO 控制台 http://localhost:9001 (admin/admin123)<br>
&emsp;6、查看mysql数据<br>
&emsp;&emsp;&emsp;```docker exec -it mysql mysql -uroot -proot123```<br>
&emsp;&emsp;查看所有数据库<br>
&emsp;&emsp;&emsp;```SHOW DATABASES;```<br>
&emsp;&emsp;使用项目数据库<br>
&emsp;&emsp;&emsp;```USE video_processing;```<br>
&emsp;&emsp;查看任务表<br>
&emsp;&emsp;&emsp;```SELECT * FROM video_tasks;```<br>
&emsp;&emsp;退出<br>
&emsp;&emsp;&emsp;```EXIT;```<br>
&emsp;7、查看minio数据<br>
&emsp;&emsp;MinIO 控制台：http://localhost:9001<br>
&emsp;&emsp;账号：admin<br>
&emsp;&emsp;密码：admin123<br>
  
**[注意项]**<br>
&emsp;1、视频剪辑部分用了GPU模式，建议更新Nvidia驱动版本以兼容加速<br>

**[项目结构]**<br>
&emsp;1、流程控制中心<br>
&emsp;&emsp;main.py<br>
&emsp;2、视频转音频→上传音频到whisper模型并接收返回的音频内容文字时间戳<br>
&emsp;&emsp;extract_audio_timestamps.py<br>
&emsp;3、删除文字时间戳里触发剪辑指令的部分<br>
&emsp;&emsp;phase1_cut.py<br>
&emsp;4、根据修改后的文字时间戳来剪辑视频，并修改视频播放速度<br>
&emsp;&emsp;edit_video1.py<br>
&emsp;5、启动端口<br>
&emsp;&emsp;app/main.py<br>

**[技术心得]**<br>
&emsp;1、识别需要剪辑的文本段采用了滑动窗口的方法，设定了两套识别规则，触发任意一条则判定为剪辑指令：规则一、如果关键词之后的两个字符在前文复现；规则二、如果关键词之后的三个字符在前文复现出两个字符位置和内容一致；<br>
&emsp;2、如何删除演讲过程中的气门？这里采用了把被编辑后的文本时间戳拼接起来的方法——也就是说最后视频只呈现存在语音的部分；<br>
