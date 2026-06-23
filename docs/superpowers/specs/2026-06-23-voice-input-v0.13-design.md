# v0.13.0 语音输入设计

## 目标

在不引入重型语音模型、不修改数据库结构的前提下，为法硕训练场景增加语音转文字能力。用户可以在苏格拉底训练页直接语音回答，也可以在错题/薄弱点录入页把语音转写填入题干、参考答案或备注。

## 方案

采用浏览器 Web Speech API 做中文语音识别：

- Chrome / Edge 支持较好，适合 Streamlit Cloud 和本地浏览器使用。
- 不上传录音文件，不新增音频存储目录。
- 转写结果作为普通文本进入现有表单和聊天流程。
- 如果浏览器不支持或麦克风权限被拒绝，页面提示用户改用文字输入。

不使用 `st.audio_input` 作为主方案，因为它只能采集音频文件，仍需要额外语音转写服务；DeepSeek 文本模型通常不能直接转写音频。

## 组件边界

新增 `components/voice_input/index.html`：

- 显示开始、停止、清空、复制按钮。
- 使用 `SpeechRecognition` / `webkitSpeechRecognition`。
- 默认语言为 `zh-CN`。
- 通过 Streamlit component protocol 回传 `{text, final_text, interim_text, language, timestamp}`。

新增 `services/voice_input.py`：

- 声明 Streamlit 自定义组件。
- 提供 `normalize_voice_payload()` 清洗组件返回值。
- 提供 `merge_voice_text()` 把新转写追加到已有草稿，避免重复追加。

## 页面接入

训练页：

- 聊天输入上方新增“语音/文字回答草稿”。
- 用户可以先语音转写，再手工修改，点击“提交草稿回答”进入原有 AI 追问流程。
- 保留原来的 `st.chat_input`，熟悉键盘输入的用户不受影响。

录入页：

- 表单上方新增“语音填入位置”：题干、参考答案、备注。
- 语音识别结果会追加到对应文本框。
- 结构化字段仍由用户确认，避免语音识别误填科目、题型或错因。

## 数据安全

本版本不新增数据库表，不迁移 schema，不保存原始音频。只有用户点击保存训练点或提交训练回答后，转写文字才进入现有数据库和溯源文件。更新不应触碰已有 `data/` 用户数据。

## 验收

- 单元测试覆盖语音 payload 清洗和文本合并。
- App 常量暴露语音输入 UI 契约。
- HTML 组件包含 `zh-CN`、`webkitSpeechRecognition` 和 `streamlit:setComponentValue`。
- 完整测试、编译检查和 Streamlit 页面 smoke 通过。
