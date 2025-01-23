class TranslationDict(dict):
    def __missing__(self, key):
        return self.get("en", "")
PROGRAM_NAME = "AutoSubSync"
TOOLTIP_SAVE_TO_DESKTOP = {
    "en": "Check this box if you want to save the new subtitle to your Desktop. If unchecked, it will be saved in the input subtitle's folder.",
    "es": "Marque esta casilla si desea guardar el nuevo subtítulo en su escritorio. Si no está marcado, se guardará en la carpeta del subtítulo de entrada.",
    "tr": "Yeni altyazıyı masaüstüne kaydetmek istiyorsanız bu kutuyu işaretleyin. İşaretlenmezse, girdi altyazının klasörüne kaydedilecektir.",
    "zh": "如果您想将新字幕保存到桌面，请选中此框。如果未选中，它将保存在输入字幕的文件夹中。",
    "ru": "Отметьте этот флажок, если хотите сохранить новый субтитр на рабочем столе. Если флажок не установлен, он будет сохранен в папке входных субтитров.",
    "pl": "Zaznacz to pole, jeśli chcesz zapisać nowe napisy na pulpicie. Jeśli nie zaznaczono, zostanie zapisany w folderze napisów wejściowych.",
    "uk": "Позначте цей прапорець, якщо хочете зберегти нові субтитри на робочому столі. Якщо не позначено, вони будуть збережені в папці вхідних субтитрів.",
    "ja": "新しい字幕をデスクトップに保存する場合は、このボックスをチェックしてください。チェックしない場合、入力字幕のフォルダに保存されます。",
    "ko": "새 자막을 바탕 화면에 저장하려면 이 상자를 선택하세요. 선택하지 않으면 입력 자막 폴더에 저장됩니다.",
    "hi": "अगर आप नई उपशीर्षक को डेस्कटॉप पर सहेजना चाहते हैं तो इस बॉक्स को चेक करें। अगर अनचेक है, तो यह इनपुट उपशीर्षक के फ़ोल्डर में सहेजा जाएगा।"

}
TOOLTIP_REPLACE_ORIGINAL = {
    "en": "Check this box if you want to replace the input subtitle file with the new one. Please be careful. It will overwrite the current subtitle.",
    "es": "Marque esta casilla si desea reemplazar el archivo de subtítulos de entrada con el nuevo. Por favor, tenga cuidado. Sobrescribirá el subtítulo actual.",
    "tr": "Girdi altyazı dosyasını yenisiyle değiştirmek istiyorsanız bu kutuyu işaretleyin. Lütfen dikkatli olun. Mevcut altyazının üzerine yazacaktır.",
    "zh": "如果您想用新字幕文件替换输入字幕文件，请选中此框。请小心。它将覆盖当前字幕。",
    "ru": "Отметьте этот флажок, если хотите заменить входной файл субтитров новым. Пожалуйста, будьте осторожны. Он перезапишет текущие субтитры.",
    "pl": "Zaznacz to pole, jeśli chcesz zastąpić oryginalny plik napisów nowym. Zachowaj ostrożność. Spowoduje to nadpisanie bieżących napisów.",
    "uk": "Позначте цей прапорець, якщо хочете замінити вхідний файл субтитрів новим. Будьте обережні. Це перезапише поточні субтитри.",
    "ja": "入力字幕ファイルを新しいものに置き換える場合は、このボックスをチェックしてください。ご注意ください。現在の字幕が上書きされます。",
    "ko": "입력 자막 파일을 새 파일로 교체하려면 이 상자를 선택하세요. 주의하세요. 현재 자막을 덮어씁니다.",
    "hi": "यदि आप इनपुट उपशीर्षक फ़ाइल को नई फ़ाइल से बदलना चाहते हैं तो इस बॉक्स को चेक करें। कृपया सावधान रहें। यह वर्तमान उपशीर्षक को अधिलेखित कर देगा।"
}
TOOLTIP_GSS = {
    "en": "--gss: Use golden-section search to find the optimal ratio between video and subtitle framerates (by default, only a few common ratios are evaluated)",
    "es": "--gss: Utilice la búsqueda de sección áurea para encontrar la proporción óptima entre las tasas de fotogramas de video y subtítulos (por defecto, solo se evalúan algunas proporciones comunes)",
    "tr": "--gss: Video ve altyazı kare hızları arasındaki en uygun oranı bulmak için altın oran aramasını kullanın (varsayılan olarak, yalnızca birkaç yaygın oran değerlendirilir)",
    "zh": "--gss: 使用黄金分割搜索来找到视频和字幕帧速率之间的最佳比例（默认情况下，仅评估一些常见的比例）",
    "ru": "--gss: Используйте поиск золотого сечения для нахождения оптимального соотношения между частотами кадров видео и субтитров (по умолчанию оцениваются только несколько общих соотношений)",
    "pl": "--gss: Użyj algorytmu złotego podziału do znalezienia optymalnego stosunku między częstotliwością klatek wideo a napisów (domyślnie oceniane są tylko niektóre powszechne proporcje)",
    "uk": "--gss: Використовуйте пошук золотого перетину для знаходження оптимального співвідношення між частотою кадрів відео та субтитрів (за замовчуванням оцінюються лише кілька поширених співвідношень)",
    "ja": "--gss: 動画と字幕のフレームレートの最適な比率を見つけるために黄金分割探索を使用します（デフォルトでは、一般的な比率のみが評価されます）",
    "ko": "--gss: 비디오와 자막 프레임 속도 간의 최적 비율을 찾기 위해 황금 분할 검색을 사용합니다 (기본적으로 일반적인 비율만 평가됨)",
    "hi": "--gss: वीडियो और उपशीर्षक फ्रेमरेट के बीच इष्टतम अनुपात खोजने के लिए स्वर्ण-खंड खोज का उपयोग करें (डिफ़ॉल्ट रूप से, केवल कुछ सामान्य अनुपातों का मूल्यांकन किया जाता है)"
}
TOOLTIP_VAD = {
    "en": "--vad=auditok: Auditok can sometimes work better in the case of low-quality audio than WebRTC's VAD. Auditok does not specifically detect voice, but instead detects all audio; this property can yield suboptimal syncing behavior when a proper VAD can work well, but can be effective in some cases.",
    "es": "--vad=auditok: Auditok a veces puede funcionar mejor en el caso de audio de baja calidad que el VAD de WebRTC. Auditok no detecta específicamente la voz, sino que detecta todo el audio; esta propiedad puede producir un comportamiento de sincronización subóptimo cuando un VAD adecuado puede funcionar bien, pero puede ser efectivo en algunos casos.",
    "tr": "--vad=auditok: Auditok, düşük kaliteli ses durumunda bazen WebRTC'nin VAD'sinden daha iyi çalışabilir. Auditok, özellikle sesi algılamaz, bunun yerine tüm sesleri algılar; bu özellik, uygun bir VAD'nin iyi çalışabileceği durumlarda optimal olmayan senkronizasyon davranışına neden olabilir, ancak bazı durumlarda etkili olabilir.",
    "zh": "--vad=auditok: 在低质量音频的情况下，Auditok 有时比 WebRTC 的 VAD 更有效。Auditok 不专门检测语音，而是检测所有音频；这种特性在适当的 VAD 可以正常工作时可能会产生次优的同步行为，但在某些情况下可能会有效。",
    "ru": "--vad=auditok: Auditok иногда может работать лучше в случае низкокачественного аудио, чем VAD WebRTC. Auditok не определяет голос, а вместо этого определяет весь аудио; это свойство может привести к субоптимальному поведению синхронизации, когда правильный VAD может работать хорошо, но может быть эффективным в некоторых случаях.",
    "pl": "--vad=auditok: Auditok może czasami działać lepiej w przypadku dźwięku niskiej jakości niż VAD WebRTC. Auditok nie wykrywa konkretnie głosu, ale wykrywa wszystkie dźwięki; ta właściwość może prowadzić do nieoptymalnej synchronizacji, gdy właściwy VAD może działać dobrze, ale może być skuteczna w niektórych przypadkach.",
    "uk": "--vad=auditok: Auditok іноді може працювати краще у випадку низькоякісного аудіо, ніж VAD WebRTC. Auditok не виявляє конкретно голос, а виявляє все аудіо; ця властивість може призвести до неоптимальної синхронізації, коли правильний VAD може працювати добре, але може бути ефективним у деяких випадках.",
    "ja": "--vad=auditok: 低品質の音声の場合、AuditokはWebRTCのVADよりも効果的に動作することがあります。Auditokは特に音声を検出するのではなく、すべての音声を検出します。この特性は、適切なVADが効果的に機能する場合に最適ではない同期動作をもたらす可能性がありますが、場合によっては効果的な場合があります。",
    "ko": "--vad=auditok: 저품질 오디오의 경우 Auditok이 WebRTC의 VAD보다 더 잘 작동할 수 있습니다. Auditok은 특별히 음성을 감지하지 않고 모든 오디오를 감지합니다. 이 특성은 적절한 VAD가 잘 작동할 수 있는 경우 차선의 동기화 동작을 초래할 수 있지만 일부 경우에는 효과적일 수 있습니다.",
    "hi": "--vad=auditok: कम गुणवत्ता वाले ऑडियो के मामले में Auditok कभी-कभी WebRTC के VAD से बेहतर काम कर सकता है। Auditok विशेष रूप से आवाज का पता नहीं लगाता है, बल्कि सभी ऑडियो का पता लगाता है; यह गुण उप-इष्टतम सिंक व्यवहार का कारण बन सकता है जब उचित VAD अच्छी तरह से काम कर सकता है, लेकिन कुछ मामलों में प्रभावी हो सकता है।"
}
TOOLTIP_FRAMERATE = {
    "en": "--no-fix-framerate: If specified, ffsubsync will not attempt to correct a framerate mismatch between reference and subtitles. This can be useful when you know that the video and subtitle framerates are same, only the subtitles are out of sync.",
    "es": "--no-fix-framerate: Si se especifica, ffsubsync no intentará corregir una discrepancia de velocidad de fotogramas entre la referencia y los subtítulos. Esto puede ser útil cuando sabes que las tasas de fotogramas de video y subtítulos son las mismas, solo los subtítulos están desincronizados.",
    "tr": "--no-fix-framerate: Belirtilirse, ffsubsync referans ve altyazılar arasındaki kare hızı uyumsuzluğunu düzeltmeye çalışmaz. Bu, video ve altyazı kare hızlarının aynı olduğunu bildiğinizde, yalnızca altyazıların senkronize olmadığında yararlı olabilir.",
    "zh": "--no-fix-framerate: 如果指定，ffsubsync 将不会尝试纠正参考和字幕之间的帧速率不匹配。当您知道视频和字幕帧速率相同时，这可能很有用，只是字幕不同步。",
    "ru": "--no-fix-framerate: Если указано, ffsubsync не будет пытаться исправить несоответствие частоты кадров между эталонным видео и субтитрами. Это может быть полезно, когда вы знаете, что частоты кадров видео и субтитров совпадают, только субтитры не синхронизированы.",
    "pl": "--no-fix-framerate: Jeśli określone, ffsubsync nie będzie próbował korygować niedopasowania częstotliwości klatek między materiałem referencyjnym a napisami. Może to być przydatne, gdy wiesz, że częstotliwości klatek wideo i napisów są takie same, tylko napisy są niezsynchronizowane.",
    "uk": "--no-fix-framerate: Якщо вказано, ffsubsync не намагатиметься виправити невідповідність частоти кадрів між довідковим відео та субтитрами. Це може бути корисно, коли ви знаєте, що частота кадрів відео та субтитрів однакова, лише субтитри не синхронізовані.",
    "ja": "--no-fix-framerate: 指定された場合、ffsubsyncは参照とサブタイトル間のフレームレートの不一致を修正しようとしません。これは、動画とサブタイトルのフレームレートが同じで、サブタイトルだけが同期していないことがわかっている場合に便利です。",
    "ko": "--no-fix-framerate: 지정된 경우, ffsubsync는 참조와 자막 간의 프레임 속도 불일치를 수정하지 않습니다. 비디오와 자막의 프레임 속도가 동일하고 자막만 동기화되지 않은 경우에 유용할 수 있습니다.",
    "hi": "--no-fix-framerate: यदि निर्दिष्ट है, तो ffsubsync संदर्भ और उपशीर्षक के बीच फ्रेमरेट बेमेल को सुधारने का प्रयास नहीं करेगा। यह तब उपयोगी हो सकता है जब आप जानते हैं कि वीडियो और उपशीर्षक फ्रेमरेट समान हैं, केवल उपशीर्षक असिंक हैं।"
}
TOOLTIP_ALASS_SPEED_OPTIMIZATION = {
    "en": "--speed optimization 0: Disable speed optimization for better accuracy. This will increase the processing time.",
    "es": "--speed optimization 0: Deshabilite la optimización de velocidad para una mejor precisión. Esto aumentará el tiempo de procesamiento.",
    "tr": "--speed optimization 0: Daha iyi doğruluk için hız optimizasyonunu devre dışı bırakın. Bu, işlem süresini artıracaktır.",
    "zh": "--speed optimization 0: 禁用速度优化以获得更高的准确性。这将增加处理时间。",
    "ru": "--speed optimization 0: Отключить оптимизацию скорости для лучшей точности. Это увеличит время обработки.",
    "pl": "--speed optimization 0: Wyłącz optymalizację prędkości dla lepszej dokładności. Wydłuży to czas przetwarzania.",
    "uk": "--speed optimization 0: Вимкніть оптимізацію швидкості для кращої точності. Це збільшить час обробки.",
    "ja": "--speed optimization 0: より良い精度のために速度最適化を無効にします。処理時間が増加します。",
    "ko": "--speed optimization 0: 더 나은 정확도를 위해 속도 최적화를 비활성화합니다. 처리 시간이 증가합니다.",
    "hi": "--speed optimization 0: बेहतर सटीकता के लिए गति अनुकूलन को अक्षम करें। यह प्रसंस्करण समय बढ़ा देगा।"
}
TOOLTIP_ALASS_DISABLE_FPS_GUESSING = {
    "en": "--disable-fps-guessing: Disables guessing and correcting of framerate differences between reference file and input file.",
    "es": "--disable-fps-guessing: Deshabilita la adivinación y corrección de diferencias de velocidad de fotogramas entre el archivo de referencia y el archivo de entrada.",
    "tr": "--disable-fps-guessing: Referans dosya ile giriş dosyası arasındaki kare hızı farklarını tahmin etmeyi ve düzeltmeyi devre dışı bırakır.",
    "zh": "--disable-fps-guessing: 禁用参考文件和输入文件之间帧速率差异的猜测和校正。",
    "ru": "--disable-fps-guessing: Отключает угадывание и коррекцию различий частоты кадров между файлом справки и входным файлом.",
    "pl": "--disable-fps-guessing: Wyłącza zgadywanie i korygowanie różnic w częstotliwości klatek między plikiem referencyjnym a plikiem wejściowym.",
    "uk": "--disable-fps-guessing: Вимикає вгадування та виправлення різниці частоти кадрів між довідковим файлом та вхідним файлом.",
    "ja": "--disable-fps-guessing: 参照ファイルと入力ファイル間のフレームレートの違いの推測と修正を無効にします。",
    "ko": "--disable-fps-guessing: 참조 파일과 입력 파일 간의 프레임 속도 차이 추측 및 수정을 비활성화합니다.",
    "hi": "--disable-fps-guessing: संदर्भ फ़ाइल और इनपुट फ़ाइल के बीच फ्रेमरेट अंतर का अनुमान लगाने और सुधार को अक्षम करता है।"
}
TOOLTIP_TEXT_ACTION_MENU_AUTO = {
    "en": "Choose what to do with the synchronized subtitle file(s). (Existing subtitle files will be backed up in the same folder, if they need to be replaced.)",
    "es": "Elija qué hacer con el/los archivo(s) de subtítulos sincronizados. (Los archivos de subtítulos existentes se respaldarán en la misma carpeta, si necesitan ser reemplazados.)",
    "tr": "Senkronize edilmiş altyazı dosyası/dosyaları ile ne yapılacağını seçin. (Mevcut altyazı dosyaları değiştirilmesi gerekiyorsa aynı klasörde yedeklenecektir.)",
    "zh": "选择如何处理同步的字幕文件。（如果需要替换现有字幕文件，它们将在同一文件夹中备份。）",
    "ru": "Выберите, что делать с синхронизированным(и) файлом(ами) субтитров. (Существующие файлы субтитров будут скопированы в ту же папку, если их нужно заменить.)",
    "pl": "Wybierz, co zrobić z zsynchronizowanym(i) plikiem(ami) napisów. (Istniejące pliki napisów zostaną zarchiwizowane w tym samym folderze, jeśli wymagają zastąpienia.)",
    "uk": "Виберіть, що робити з синхронізованим(и) файлом(ами) субтитрів. (Наявні файли субтитрів будуть збережені в тій же папці, якщо їх потрібно замінити.)",
    "ja": "同期した字幕ファイルの処理方法を選択してください。（既存の字幕ファイルは、置き換える必要がある場合、同じフォルダにバックアップされます。）",
    "ko": "동기화된 자막 파일을 어떻게 처리할지 선택하세요. (기존 자막 파일을 교체해야 하는 경우 같은 폴더에 백업됩니다.)",
    "hi": "सिंक्रनाइज़ की गई उपशीर्षक फ़ाइल(ों) के साथ क्या करना है, चुनें। (मौजूदा उपशीर्षक फ़ाइलें उसी फ़ोल्डर में बैकअप की जाएंगी, यदि उन्हें बदलने की आवश्यकता है।)"
}
TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO = {
    "en": "Select the tool to use for synchronization.",
    "es": "Seleccione la herramienta a utilizar para la sincronización.",
    "tr": "Senkronizasyon için kullanılacak aracı seçin.",
    "zh": "选择用于同步的工具。",
    "ru": "Выберите инструмент для синхронизации.",
    "pl": "Wybierz narzędzie do synchronizacji.",
    "uk": "Виберіть інструмент для синхронізації.",
    "ja": "同期に使用するツールを選択してください。",
    "ko": "동기화에 사용할 도구를 선택하세요.",
    "hi": "सिंक्रनाइज़ेशन के लिए उपकरण चुनें।"
}
UPDATE_AVAILABLE_TITLE = {
    "en": "Update Available",
    "es": "Actualización Disponible",
    "tr": "Güncelleme Mevcut",
    "zh": "有可用更新",
    "ru": "Доступно обновление",
    "pl": "Dostępna Aktualizacja",
    "uk": "Доступне Оновлення",
    "ja": "アップデートが利用可能",
    "ko": "업데이트 가능",
    "hi": "अपडेट उपलब्ध"
}
UPDATE_AVAILABLE_TEXT = {
    "en": "A new version ({latest_version}) is available. Do you want to update?",
    "es": "Una nueva versión ({latest_version}) está disponible. ¿Quieres actualizar?",
    "tr": "Yeni bir sürüm ({latest_version}) mevcut. Güncellemek istiyor musunuz?",
    "zh": "有新版本 ({latest_version}) 可用。您想更新吗？",
    "ru": "Доступна новая версия ({latest_version}). Хотите обновить?",
    "pl": "Nowa wersja ({latest_version}) jest dostępna. Czy chcesz zaktualizować?",
    "uk": "Доступна нова версія ({latest_version}). Бажаєте оновити?",
    "ja": "新しいバージョン({latest_version})が利用可能です。アップデートしますか？",
    "ko": "새 버전({latest_version})이 있습니다. 업데이트하시겠습니까?",
    "hi": "एक नया संस्करण ({latest_version}) उपलब्ध है। क्या आप अपडेट करना चाहते हैं?"
}
NOTIFY_ABOUT_UPDATES_TEXT = {
    "en": "Check for updates",
    "es": "Buscar actualizaciones",
    "tr": "Güncellemeleri kontrol et",
    "zh": "检查更新",
    "ru": "Проверить обновления",
    "pl": "Sprawdź aktualizacje",
    "uk": "Перевірити оновлення",
    "ja": "アップデートを確認",
    "ko": "업데이트 확인",
    "hi": "अपडेट के लिए जाँच करें"
}
LANGUAGE_LABEL_TEXT = {
    "en": "Language",
    "es": "Idioma",
    "tr": "Dil",
    "zh": "语言",
    "ru": "Язык",
    "pl": "Język",
    "uk": "Мова",
    "ja": "言語",
    "ko": "언어",
    "hi": "भाषा"
}
# TEXT SHOULD BE SHORT
TAB_AUTOMATIC_SYNC = {
    "en": 'Automatic Sync',
    "es": 'Sinc. Automática',
    "tr": 'Otomatik Senkr.',
    "zh": '自动同步',
    "ru": 'Автомат. синхр.',
    "pl": "Autom. Synchr.",
    "uk": "Автом. Синхр.",
    "ja": "自動同期",
    "ko": "자동 동기화",
    "hi": "स्वचालित सिंक"
}
# TEXT SHOULD BE SHORT
TAB_MANUAL_SYNC = {
    "en": 'Manual Sync',
    "es": 'Sinc. Manual',
    "tr": 'Manuel Senk.',
    "zh": '手动同步',
    "ru": 'Ручная синхр.',
    "pl": "Ręczna Synchr.",
    "uk": "Ручна Синхр.",
    "ja": "手動同期",
    "ko": "수동 동기화",
    "hi": "मैनुअल सिंक"
}
CANCEL_TEXT = {
    "en": 'Cancel',
    "es": 'Cancelar',
    "tr": 'İptal',
    "zh": '取消',
    "ru": 'Отмена',
    "pl": "Anuluj",
    "uk": "Скасувати",
    "ja": "キャンセル",
    "ko": "취소",
    "hi": "रद्द करें"
}
GENERATE_AGAIN_TEXT = {
    "en": 'Generate Again',
    "es": 'Generar de Nuevo',
    "tr": 'Tekrar Oluştur',
    "zh": '再次生成',
    "ru": 'Сгенерировать снова',
    "pl": "Wygeneruj Ponownie",
    "uk": "Згенерувати Знову",
    "ja": "再生成",
    "ko": "다시 생성",
    "hi": "फिर से जनरेट करें"
}
GO_BACK = {
    "en": 'Go Back',
    "es": 'Regresar',
    "tr": 'Geri Dön',
    "zh": '返回',
    "ru": 'Вернуться',
    "pl": "Wróć",
    "uk": "Назад",
    "ja": "戻る",
    "ko": "돌아가기",
    "hi": "वापस जाएं"

}
BATCH_MODE_TEXT = {
    "en": 'Batch Mode',
    "es": 'Modo por Lotes',
    "tr": 'Toplu Mod',
    "zh": '批处理模式',
    "ru": 'Пакетный режим',
    "pl": "Tryb Wsadowy",
    "uk": "Пакетний Режим",
    "ja": "バッチモード",
    "ko": "일괄 처리 모드",
    "hi": "बैच मोड"
}
NORMAL_MODE_TEXT = {
    "en": 'Normal Mode',
    "es": 'Modo Normal',
    "tr": 'Normal Mod',
    "zh": '正常模式',
    "ru": 'Обычный режим',
    "pl": "Tryb Normalny",
    "uk": "Звичайний Режим",
    "ja": "通常モード",
    "ko": "일반 모드",
    "hi": "सामान्य मोड"
}
# TEXT SHOULD BE SHORT
START_AUTOMATIC_SYNC_TEXT = {
    "en": 'Start Automatic Sync',
    "es": 'Iniciar Sinc. Automática',
    "tr": 'Otomatik Senkr. Başlat',
    "zh": "开始自动同步",
    "ru": 'Начать автосинхронизацию',
    "pl": "Rozpocznij Autom. Synchr.",
    "uk": "Почати Автом. Синхр.",
    "ja": "自動同期開始",
    "ko": "자동 동기화 시작",
    "hi": "स्वचालित सिंक शुरू करें"
}
# TEXT SHOULD BE SHORT
START_BATCH_SYNC_TEXT = {
    "en": 'Start Batch Sync',
    "es": 'Iniciar Sincr. por Lotes',
    "tr": 'Toplu Senkr. Başlat',
    "zh": "开始批量同步",
    "ru": 'Начать пакетную синхр.',
    "pl": "Rozpocznij Synchr. Wsadową",
    "uk": "Почати Пакетну Синхр.",
    "ja": "バッチ同期開始",
    "ko": "일괄 동기화 시작",
    "hi": "बैच सिंक शुरू करें"
}
BATCH_INPUT_TEXT = {
    "en": "Drag and drop multiple files/folders here or click to browse.\n\n(Videos and subtitles that have the same filenames will be paired automatically. You need to pair others manually.)",
    "es": "Arrastre y suelte varios archivos/carpetas aquí o haga clic para buscar.\n\n(Los videos y subtítulos que tienen los mismos nombres de archivo se emparejarán automáticamente. Debe emparejar otros manualmente.)",
    "tr": "Birden fazla dosya/klasörü buraya sürükleyip bırakın veya göz atmak için tıklayın.\n\n(Aynı dosya adlarına sahip videolar ve altyazılar otomatik olarak eşleştirilecektir. Diğerlerini manuel olarak eşleştirmeniz gerekir.)",
    "zh": "将多个文件/文件夹拖放到此处或点击浏览。\n\n(具有相同文件名的视频和字幕将自动配对。您需要手动配对其他文件。)",
    "ru": "Перетащите несколько файлов/папок сюда или нажмите, чтобы выбрать.\n\n(Видео и субтитры с одинаковыми именами файлов будут автоматически сопоставлены. Для других вам нужно будет сопоставить вручную.)",
    "pl": "Przeciągnij i upuść wiele plików/folderów tutaj lub kliknij, aby przeglądać.\n\n(Filmy i napisy o tych samych nazwach plików zostaną automatycznie sparowane. Inne trzeba sparować ręcznie.)",
    "uk": "Перетягніть декілька файлів/папок сюди або натисніть для вибору.\n\n(Відео та субтитри з однаковими іменами файлів будуть автоматично поєднані. Інші потрібно поєднати вручну.)",
    "ja": "複数のファイル/フォルダをここにドラッグ＆ドロップするか、クリックして参照してください。\n\n(同じファイル名を持つ動画と字幕は自動的にペアになります。他のものは手動でペアにする必要があります。)",
    "ko": "여러 파일/폴더를 여기에 끌어다 놓거나 클릭하여 찾아보세요.\n\n(동일한 파일 이름을 가진 비디오와 자막은 자동으로 짝지어집니다. 다른 파일들은 수동으로 짝지어야 합니다.)",
    "hi": "कई फ़ाइलों/फ़ोल्डरों को यहाँ खींचें और छोड़ें या ब्राउज़ करने के लिए क्लिक करें।\n\n(समान फ़ाइल नामों वाले वीडियो और उपशीर्षक स्वचालित रूप से जोड़े जाएंगे। अन्य को मैन्युअल रूप से जोड़ना होगा।)"
}
BATCH_INPUT_LABEL_TEXT = {
    "en": "Batch Processing Mode",
    "es": "Modo de Procesamiento por Lotes",
    "tr": "Toplu İşleme Modu",
    "zh": "批处理模式",
    "ru": "Режим пакетной обработки",
    "pl": "Tryb Przetwarzania Wsadowego",
    "uk": "Режим Пакетної Обробки",
    "ja": "バッチ処理モード",
    "ko": "일괄 처리 모드",
    "hi": "बैच प्रोसेसिंग मोड"
}
SHIFT_SUBTITLE_TEXT = {
    "en": 'Shift Subtitle',
    "es": 'Desplazar Subtítulo',
    "tr": 'Altyazıyı Kaydır',
    "zh": '移位字幕',
    "ru": 'Сдвиг субтитров',
    "pl": "Przesuń Napisy",
    "uk": "Зсунути Субтитри",
    "ja": "字幕をシフト",
    "ko": "자막 이동",
    "hi": "उपशीर्षक शिफ्ट करें"
}
LABEL_SHIFT_SUBTITLE = {
    "en": "Shift subtitle by (ms):",
    "es": "Desplazar subtítulo (ms):",
    "tr": "Altyazıyı kaydır (ms):",
    "zh": "移位字幕（毫秒）：",
    "ru": "Сдвинуть субтитры на (мс):",
    "pl": "Przesuń napisy o (ms):",
    "uk": "Зсунути субтитри на (мс):",
    "ja": "字幕をシフト (ミリ秒):",
    "ko": "자막 이동 (밀리초):",
    "hi": "उपशीर्षक को शिफ्ट करें (मिली सेकंड):"
}
REPLACE_ORIGINAL_TITLE = {
    "en": "Subtitle Change Confirmation",
    "es": "Confirmación de Cambio de Subtítulo",
    "tr": "Altyazı Değişikliği Onayı",
    "zh": "字幕更改确认",
    "ru": "Подтверждение изменения субтитров",
    "pl": "Potwierdzenie Zmiany Napisów",
    "uk": "Підтвердження Зміни Субтитрів",
    "ja": "字幕変更の確認",
    "ko": "자막 변경 확인",
    "hi": "उपशीर्षक परिवर्तन पुष्टि"
}
REPLACE_ORIGINAL_TEXT = {
    "en": "Adjusting again by {milliseconds}ms, will make a total difference of {total_shifted}ms. Proceed?",
    "es": "Ajustar nuevamente por {milliseconds}ms, hará una diferencia total de {total_shifted}ms. ¿Proceder?",
    "tr": "{milliseconds}ms kadar yeniden ayarlamak, toplamda {total_shifted}ms fark yaratacaktır. Devam edilsin mi?",
    "zh": "再次调整 {milliseconds} 毫秒，总共将差 {total_shifted} 毫秒。继续吗？",
    "ru": "Повторная настройка на {milliseconds} мс создаст общую разницу в {total_shifted} мс. Продолжить?",
    "pl": "Ponowna regulacja o {milliseconds}ms spowoduje całkowitą różnicę {total_shifted}ms. Kontynuować?",
    "uk": "Повторне налаштування на {milliseconds}мс створить загальну різницю в {total_shifted}мс. Продовжити?",
    "ja": "さらに{milliseconds}ミリ秒調整すると、合計{total_shifted}ミリ秒の差になります。続行しますか？",
    "ko": "다시 {milliseconds}ms 조정하면 총 {total_shifted}ms의 차이가 생깁니다. 계속하시겠습니까?",
    "hi": "{milliseconds}ms से पुनः समायोजन करने से कुल {total_shifted}ms का अंतर होगा। आगे बढ़ें?"
}
FILE_EXISTS_TITLE = {
    "en": "File Exists",
    "es": "El Archivo Existe",
    "tr": "Dosya Mevcut",
    "zh": "文件已存在",
    "ru": "Файл существует",
    "pl": "Plik Istnieje",
    "uk": "Файл Існує",
    "ja": "ファイルが存在します",
    "ko": "파일이 존재함",
    "hi": "फ़ाइल मौजूद है"
}
FILE_EXISTS_TEXT = {
    "en": "A file with the name '{filename}' already exists. Do you want to replace it?",
    "es": "Un archivo con el nombre '{filename}' ya existe. ¿Desea reemplazarlo?",
    "tr": "'{filename}' adında bir dosya zaten var. Değiştirmek istiyor musunuz?",
    "zh": "名为 '{filename}' 的文件已存在。您要替换它吗？",
    "ru": "Файл с именем '{filename}' уже существует. Хотите заменить его?",
    "pl": "Plik o nazwie '{filename}' już istnieje. Czy chcesz go zastąpić?",
    "uk": "Файл з іменем '{filename}' вже існує. Бажаєте замінити його?",
    "ja": "'{filename}'という名前のファイルは既に存在します。置き換えますか？",
    "ko": "'{filename}' 이름의 파일이 이미 존재합니다. 교체하시겠습니까?",
    "hi": "'{filename}' नाम की फ़ाइल पहले से मौजूद है। क्या आप इसे बदलना चाहते हैं?"
}
ALREADY_SYNCED_FILES_TITLE = {
    "en": "Already Synced Files Detected",
    "es": "Archivos Ya Sincronizados Detectados",
    "tr": "Zaten Senkronize Edilmiş Dosyalar Tespit Edildi",
    "zh": "检测到已同步的文件",
    "ru": "Обнаружены уже синхронизированные файлы",
    "pl": "Wykryto Już Zsynchronizowane Pliki",
    "uk": "Виявлено Вже Синхронізовані Файли",
    "ja": "既に同期されたファイルが検出されました",
    "ko": "이미 동기화된 파일 감지됨",
    "hi": "पहले से सिंक की गई फ़ाइलें मिलीं"
}
ALREADY_SYNCED_FILES_MESSAGE = {
    "en": "Detected {count} subtitle(s) already synced, because there are subtitles that have 'autosync_' prefix in the same folder with same filenames. Do you want to skip processing them?",
    "es": "Se detectaron {count} subtítulo(s) ya sincronizados, porque hay subtítulos que tienen el prefijo 'autosync_' en la misma carpeta con los mismos nombres de archivo. ¿Desea omitir su procesamiento?",
    "tr": "Aynı klasörde aynı dosya adlarına sahip 'autosync_' öneki olan altyazılar olduğu için {count} altyazı zaten senkronize edilmiş olarak tespit edildi. Bu altyazıların tekrar işlenmesini atlamak istiyor musunuz?",
    "zh": "检测到 {count} 个字幕已同步，因为在同一文件夹中有带有 'autosync_' 前缀的字幕，文件名相同。您要跳过处理它们吗？",
    "ru": "Обнаружено {count} субтитров уже синхронизировано, потому что есть субтитры с префиксом 'autosync_' в той же папке с теми же именами файлов. Хотите пропустить их обработку?",
    "pl": "Wykryto {count} napisów już zsynchronizowanych, ponieważ w tym samym folderze znajdują się napisy z przedrostkiem 'autosync_' o tych samych nazwach plików. Czy chcesz pominąć ich przetwarzanie?",
    "uk": "Виявлено {count} субтитрів вже синхронізовано, тому що є субтитри з префіксом 'autosync_' у тій же папці з тими ж іменами файлів. Бажаєте пропустити їх обробку?",
    "ja": "同じフォルダ内に'autosync_'プレフィックスを持つ同じファイル名の字幕があるため、{count}個の字幕が既に同期されていることが検出されました。これらの処理をスキップしますか？",
    "ko": "동일한 폴더에 'autosync_' 접두사가 있는 동일한 파일 이름의 자막이 있어서 {count}개의 자막이 이미 동기화된 것으로 감지되었습니다. 이들의 처리를 건너뛰시겠습니까?",
    "hi": "{count} उपशीर्षक पहले से सिंक किए गए पाए गए, क्योंकि समान फ़ोल्डर में 'autosync_' उपसर्ग वाले समान फ़ाइल नामों के उपशीर्षक हैं। क्या आप उनके प्रसंस्करण को छोड़ना चाहते हैं?"
}
SUBTITLE_INPUT_TEXT = {
    "en": "Drag and drop the unsynchronized subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de subtítulos no sincronizado aquí o haga clic para buscar.",
    "tr": "Senkronize edilmemiş altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın.",
    "zh": "将未同步的字幕文件拖放到此处或点击浏览。",
    "ru": "Перетащите несинхронизированный файл субтитров сюда или нажмите, чтобы выбрать.",
    "pl": "Przeciągnij i upuść niesynchronizowany plik napisów tutaj lub kliknij, aby przeglądać.",
    "uk": "Перетягніть несинхронізований файл субтитрів сюди або натисніть для вибору.",
    "ja": "未同期の字幕ファイルをここにドラッグ＆ドロップするか、クリックして参照してください。",
    "ko": "동기화되지 않은 자막 파일을 여기에 끌어다 놓거나 클릭하여 찾아보세요.",
    "hi": "असिंक्रनाइज़्ड उपशीर्षक फ़ाइल को यहाँ खींचें और छोड़ें या ब्राउज़ करने के लिए क्लिक करें।"
}
VIDEO_INPUT_TEXT = {
    "en": "Drag and drop video or reference subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de video o subtítulos de referencia aquí o haga clic para buscar.",
    "tr": "Video veya referans altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın.",
    "zh": "将视频或参考字幕文件拖放到此处或点击浏览。",
    "ru": "Перетащите видео или файл справочных субтитров сюда или нажмите, чтобы выбрать.",
    "pl": "Przeciągnij i upuść plik wideo lub referencyjny plik napisów tutaj lub kliknij, aby przeglądać.",
    "uk": "Перетягніть відео або файл довідкових субтитрів сюди або натисніть для вибору.",
    "ja": "動画または参照字幕ファイルをここにドラッグ＆ドロップするか、クリックして参照してください。",
    "ko": "비디오 또는 참조 자막 파일을 여기에 끌어다 놓거나 클릭하여 찾아보세요.",
    "hi": "वीडियो या संदर्भ उपशीर्षक फ़ाइल को यहाँ खींचें और छोड़ें या ब्राउज़ करने के लिए क्लिक करें।"
}
LABEL_DROP_BOX = {
    "en": "Drag and drop subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de subtítulos aquí o haga clic para buscar.",
    "tr": "Altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın.",
    "zh": "将字幕文件拖放到此处或点击浏览。",
    "ru": "Перетащите файл субтитров сюда или нажмите, чтобы выбрать.",
    "pl": "Przeciągnij i upuść plik napisów tutaj lub kliknij, aby przeglądać.",
    "uk": "Перетягніть файл субтитрів сюди або натисніть для вибору.",
    "ja": "字幕ファイルをここにドラッグ＆ドロップするか、クリックして参照してください。",
    "ko": "자막 파일을 여기에 끌어다 놓거나 클릭하여 찾아보세요.",
    "hi": "उपशीर्षक फ़ाइल को यहाँ खींचें और छोड़ें या ब्राउज़ करने के लिए क्लिक करें।"
}
WARNING = {
    "en": "Warning",
    "es": "Advertencia",
    "tr": "Uyarı",
    "zh": "警告",
    "ru": "Предупреждение",
    "pl": "Ostrzeżenie",
    "uk": "Попередження",
    "ja": "警告",
    "ko": "경고",
    "hi": "चेतावनी"
}
CONFIRM_RESET_MESSAGE = {
    "en": "Are you sure you want to reset settings to default values?",
    "es": "¿Está seguro de que desea restablecer la configuración a los valores predeterminados?",
    "tr": "Ayarları varsayılan değerlere sıfırlamak istediğinizden emin misiniz?",
    "zh": "您确定要将设置重置为默认值吗？",
    "ru": "Вы уверены, что хотите сбросить настройки на значения по умолчанию?",
    "pl": "Czy na pewno chcesz przywrócić ustawienia do wartości domyślnych?",
    "uk": "Ви впевнені, що хочете скинути налаштування до значень за замовчуванням?",
    "ja": "設定をデフォルト値にリセットしてもよろしいですか？",
    "ko": "설정을 기본값으로 재설정하시겠습니까?",
    "hi": "क्या आप वाकई सेटिंग्स को डिफ़ॉल्ट मान पर रीसेट करना चाहते हैं?"
}
TOGGLE_KEEP_CONVERTED_SUBTITLES_WARNING = {
    "en": 'Subtitles with "converted_subtitlefilename" in the output folder will be deleted automatically. Do you want to continue?',
    "es": 'Los subtítulos con "converted_subtitlefilename" en la carpeta de salida se eliminarán automáticamente. ¿Desea continuar?',
    "tr": 'Çıktı klasöründe "converted_subtitlefilename" olan altyazılar otomatik olarak silinecektir. Devam etmek istiyor musunuz?',
    "zh": '输出文件夹中带有 "converted_subtitlefilename" 的字幕将自动删除。您要继续吗？',
    "ru": 'Субтитры с "converted_subtitlefilename" в папке вывода будут автоматически удалены. Хотите продолжить?',
    "pl": 'Napisy z "converted_subtitlefilename" w folderze wyjściowym zostaną automatycznie usunięte. Czy chcesz kontynuować?',
    "uk": 'Субтитри з "converted_subtitlefilename" у вихідній папці будуть автоматично видалені. Бажаєте продовжити?',
    "ja": '出力フォルダ内の "converted_subtitlefilename" を含む字幕は自動的に削除されます。続行しますか？',
    "ko": '출력 폴더의 "converted_subtitlefilename"이 포함된 자막이 자동으로 삭제됩니다. 계속하시겠습니까?',
    "hi": 'आउटपुट फ़ोल्डर में "converted_subtitlefilename" वाले उपशीर्षक स्वचालित रूप से हटा दिए जाएंगे। क्या आप जारी रखना चाहते हैं?'
}
TOGGLE_KEEP_EXTRACTED_SUBTITLES_WARNING = {
    "en": 'Folders with "extracted_subtitles_videofilename" in the output folder will be deleted automatically. Do you want to continue?',
    "es": 'Las carpetas con "extracted_subtitles_videofilename" en la carpeta de salida se eliminarán automáticamente. ¿Desea continuar?',
    "tr": 'Çıktı klasöründe "extracted_subtitles_videofilename" olan klasörler otomatik olarak silinecektir. Devam etmek istiyor musunuz?',
    "zh": '输出文件夹中带有 "extracted_subtitles_videofilename" 的文件夹将自动删除。您要继续吗？',
    "ru": 'Папки с "extracted_subtitles_videofilename" в папке вывода будут автоматически удалены. Хотите продолжить?',
    "pl": 'Foldery z "extracted_subtitles_videofilename" w folderze wyjściowym zostaną automatycznie usunięte. Czy chcesz kontynuować?',
    "uk": 'Папки з "extracted_subtitles_videofilename" у вихідній папці будуть автоматично видалені. Бажаєте продовжити?',
    "ja": '出力フォルダ内の "extracted_subtitles_videofilename" を含むフォルダは自動的に削除されます。続行しますか？',
    "ko": '출력 폴더의 "extracted_subtitles_videofilename"이 포함된 폴더가 자동으로 삭제됩니다. 계속하시겠습니까?',
    "hi": 'आउटपुट फ़ोल्डर में "extracted_subtitles_videofilename" वाले फ़ोल्डर स्वचालित रूप से हटा दिए जाएंगे। क्या आप जारी रखना चाहते हैं?'
}
BACKUP_SUBTITLES_BEFORE_OVERWRITING_WARNING = {
    "en": "Existing subtitle files will not be backed up before overwriting. Do you want to continue?",
    "es": "Los archivos de subtítulos existentes no se respaldarán antes de sobrescribir. ¿Desea continuar?",
    "tr": "Mevcut altyazı dosyaları üzerine yazılmadan önce yedeklenmeyecektir. Devam etmek istiyor musunuz?",
    "zh": "现有字幕文件在覆盖之前不会备份。您要继续吗？",
    "ru": "Существующие файлы субтитров не будут резервироваться перед перезаписью. Хотите продолжить?",
    "pl": "Istniejące pliki napisów nie zostaną zarchiwizowane przed nadpisaniem. Czy chcesz kontynuować?",
    "uk": "Наявні файли субтитрів не будуть збережені перед перезаписом. Бажаєте продовжити?",
    "ja": "既存の字幕ファイルは上書き前にバックアップされません。続行しますか？",
    "ko": "기존 자막 파일이 덮어쓰기 전에 백업되지 않습니다. 계속하시겠습니까?",
    "hi": "मौजूदा उपशीर्षक फ़ाइलों का अधिलेखन से पहले बैकअप नहीं किया जाएगा। क्या आप जारी रखना चाहते हैं?"
}
PROMPT_ADDITIONAL_FFSUBSYNC_ARGS = {
    "en": "Enter additional arguments for ffsubsync:",
    "es": "Ingrese argumentos adicionales para ffsubsync:",
    "tr": "ffsubsync için ek argümanlar girin:",
    "zh": "输入 ffsubsync 的附加参数：",
    "ru": "Введите дополнительные аргументы для ffsubsync:",
    "pl": "Wprowadź dodatkowe argumenty dla ffsubsync:",
    "uk": "Введіть додаткові аргументи для ffsubsync:",
    "ja": "ffsubsyncの追加引数を入力してください:",
    "ko": "ffsubsync의 추가 인수를 입력하세요:",
    "hi": "ffsubsync के लिए अतिरिक्त तर्क दर्ज करें:"
}
PROMPT_ADDITIONAL_ALASS_ARGS = {
    "en": "Enter additional arguments for alass:",
    "es": "Ingrese argumentos adicionales para alass:",
    "tr": "alass için ek argümanlar girin:",
    "zh": "输入 alass 的附加参数：",
    "ru": "Введите дополнительные аргументы для alass:",
    "pl": "Wprowadź dodatkowe argumenty dla alass:",
    "uk": "Введіть додаткові аргументи для alass:",
    "ja": "alassの追加引数を入力してください:",
    "ko": "alass의 추가 인수를 입력하세요:",
    "hi": "alass के लिए अतिरिक्त तर्क दर्ज करें:"
}
LABEL_ADDITIONAL_FFSUBSYNC_ARGS = {
    "en": "Additional arguments for ffsubsync",
    "es": "Argumentos adicionales para ffsubsync",
    "tr": "ffsubsync için ek argümanlar",
    "zh": "ffsubsync 的附加参数",
    "ru": "Дополнительные аргументы для ffsubsync",
    "pl": "Dodatkowe argumenty dla ffsubsync",
    "uk": "Додаткові аргументи для ffsubsync",
    "ja": "ffsubsyncの追加引数",
    "ko": "ffsubsync의 추가 인수",
    "hi": "ffsubsync के लिए अतिरिक्त तर्क"
}
LABEL_ADDITIONAL_ALASS_ARGS = {
    "en": "Additional arguments for alass",
    "es": "Argumentos adicionales para alass",
    "tr": "alass için ek argümanlar",
    "zh": "alass 的附加参数",
    "ru": "Дополнительные аргументы для alass",
    "pl": "Dodatkowe argumenty dla alass",
    "uk": "Додаткові аргументи для alass",
    "ja": "alassの追加引数",
    "ko": "alass의 추가 인수",
    "hi": "alass के लिए अतिरिक्त तर्क"
}
LABEL_CHECK_VIDEO_FOR_SUBTITLE_STREAM = {
    "en": "Check video for subtitle streams in alass",
    "es": "Verificar video para flujos de subtítulos en alass",
    "tr": "alass'ta altyazı akışları için videoyu kontrol et",
    "zh": "在 alass 中检查视频的字幕流",
    "ru": "Проверить видео на наличие потоков субтитров в alass",
    "pl": "Sprawdź strumienie napisów w wideo w alass",
    "uk": "Перевірити відео на наявність потоків субтитрів в alass",
    "ja": "alassで字幕ストリームのビデオをチェック",
    "ko": "alass에서 자막 스트림 비디오 확인",
    "hi": "alass में उपशीर्षक स्ट्रीम के लिए वीडियो जांचें"
}
LABEL_BACKUP_SUBTITLES = {
    "en": "Backup subtitles before overwriting",
    "es": "Respaldar subtítulos antes de sobrescribir",
    "tr": "Üzerine yazmadan önce altyazıları yedekle",
    "zh": "覆盖前备份字幕",
    "ru": "Резервное копирование субтитров перед перезаписью",
    "pl": "Utwórz kopię zapasową napisów przed nadpisaniem",
    "uk": "Створити резервну копію субтитрів перед перезаписом",
    "ja": "上書き前に字幕をバックアップ",
    "ko": "덮어쓰기 전에 자막 백업",
    "hi": "अधिलेखन से पहले उपशीर्षक का बैकअप लें"
}
LABEL_KEEP_CONVERTED_SUBTITLES = {
    "en": "Keep converted subtitles",
    "es": "Mantener subtítulos convertidos",
    "tr": "Dönüştürülmüş altyazıları sakla",
    "zh": "保留转换后的字幕",
    "ru": "Сохранить конвертированные субтитры",
    "pl": "Zachowaj przekonwertowane napisy",
    "uk": "Зберегти конвертовані субтитри",
    "ja": "変換した字幕を保持",
    "ko": "변환된 자막 유지",
    "hi": "परिवर्तित उपशीर्षक रखें"
}
LABEL_KEEP_EXTRACTED_SUBTITLES = {
    "en": "Keep extracted subtitles",
    "es": "Mantener subtítulos extraídos",
    "tr": "Çıkarılan altyazıları sakla",
    "zh": "保留提取的字幕",
    "ru": "Сохранить извлеченные субтитры",
    "pl": "Zachowaj wyodrębnione napisy",
    "uk": "Зберегти витягнуті субтитри",
    "ja": "抽出した字幕を保持",
    "ko": "추출된 자막 유지",
    "hi": "निकाले गए उपशीर्षक रखें"
}
LABEL_REMEMBER_THE_CHANGES = {
    "en": "Remember the changes",
    "es": "Recordar los cambios",
    "tr": "Değişiklikleri hatırla",
    "zh": "记住更改",
    "ru": "Запомнить изменения",
    "pl": "Zapamiętaj zmiany",
    "uk": "Запам'ятати зміни",
    "ja": "変更を記憶",
    "ko": "변경 사항 기억",
    "hi": "परिवर्तन याद रखें"
}
LABEL_RESET_TO_DEFAULT_SETTINGS = {
    "en": "Reset to default settings",
    "es": "Restablecer a la configuración predeterminada",
    "tr": "Varsayılan ayarlara sıfırla",
    "zh": "重置为默认设置",
    "ru": "Сбросить настройки по умолчанию",
    "pl": "Przywróć ustawienia domyślne",
    "uk": "Скинути до налаштувань за замовчуванням",
    "ja": "デフォルト設定にリセット",
    "ko": "기본 설정으로 재설정",
    "hi": "डिफ़ॉल्ट सेटिंग्स पर रीसेट करें"
}
LABEL_KEEP_LOG_RECORDS = {
    "en": "Keep log records",
    "es": "Mantener registros",
    "tr": "Log kayıtlarını sakla",
    "zh": "保留日志记录",
    "ru": "Сохранять журналы",
    "pl": "Zachowaj logi",
    "uk": "Зберігати журнали",
    "ja": "ログを保持",
    "ko": "로그 기록 유지",
    "hi": "लॉग रिकॉर्ड रखें"
}
LABEL_OPEN_LOGS_FOLDER = {
    "en": "Open logs folder",
    "es": "Abrir carpeta de registros",
    "tr": "Log klasörünü aç",
    "zh": "打开日志文件夹",
    "ru": "Открыть папку журналов",
    "pl": "Otwórz folder logów",
    "uk": "Відкрити папку журналів",
    "ja": "ログフォルダを開く",
    "ko": "로그 폴더 열기",
    "hi": "लॉग फ़ोल्डर खोलें"
}
LABEL_CLEAR_ALL_LOGS = {
    "en": "Clear all logs",
    "es": "Borrar todos los registros",
    "tr": "Tüm logları temizle",
    "zh": "清除所有日志",
    "ru": "Очистить все журналы",
    "pl": "Wyczyść wszystkie logi",
    "uk": "Очистити всі журнали",
    "ja": "すべてのログをクリア",
    "ko": "모든 로그 지우기",
    "hi": "सभी लॉग साफ़ करें"
}
LOG_FILES_DELETE_WARNING = {
    "en": "There are {count} log files. Do you want to delete them?",
    "es": "Hay {count} archivos de registro. ¿Desea eliminarlos?",
    "tr": "{count} adet log dosyası var. Silmek istiyor musunuz?",
    "zh": "有 {count} 个日志文件。您想要删除它们吗？",
    "ru": "Есть {count} файлов журнала. Вы хотите их удалить?",
    "pl": "Istnieje {count} plików dziennika. Czy chcesz je usunąć?",
    "uk": "Є {count} файлів журналу. Ви хочете їх видалити?",
    "ja": "{count} 個のログファイルがあります。削除しますか？",
    "ko": "{count}개의 로그 파일이 있습니다. 삭제하시겠습니까?",
    "hi": "{count} लॉग फ़ाइलें हैं। क्या आप उन्हें हटाना चाहते हैं?"
}
SYNC_TOOL_FFSUBSYNC = {
    "en": "ffsubsync",
    "es": "ffsubsync",
    "tr": "ffsubsync",
    "zh": "ffsubsync",
    "ru": "ffsubsync",
    "pl": "ffsubsync",
    "uk": "ffsubsync",
    "ja": "ffsubsync",
    "ko": "ffsubsync",
    "hi": "ffsubsync"
}
SYNC_TOOL_ALASS = {
    "en": "alass",
    "es": "alass",
    "tr": "alass",
    "zh": "alass",
    "ru": "alass",
    "pl": "alass",
    "uk": "alass",
    "ja": "alass",
    "ko": "alass",
    "hi": "alass"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_NEXT_TO_SUBTITLE = {
    "en": "Save next to input subtitle",
    "es": "Guardar junto al subtítulo de entrada",
    "tr": "Girdi altyazının yanına kaydet",
    "zh": "保存在输入字幕旁",
    "ru": "Сохранить рядом с входными субтитрами",
    "pl": "Zapisz obok napisów wejściowych",
    "uk": "Зберегти поруч з вхідними субтитрами",
    "ja": "入力字幕の横に保存",
    "ko": "입력 자막 옆에 저장",
    "hi": "इनपुट उपशीर्षक के पास सहेजें"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_NEXT_TO_VIDEO = {
    "en": "Save next to video",
    "es": "Guardar junto al video",
    "tr": "Videonun yanına kaydet",
    "zh": "保存到视频旁",
    "ru": "Сохранить рядом с видео",
    "pl": "Zapisz obok wideo",
    "uk": "Зберегти поруч з відео",
    "ja": "動画の横に保存",
    "ko": "비디오 옆에 저장",
    "hi": "वीडियो के पास सहेजें"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME = {
    "en": "Save next to video with same filename",
    "es": "Guardar junto al video con el mismo nombre",
    "tr": "Videonun yanına aynı dosya adıyla kaydet",
    "zh": "与视频的同名文件保存到视频旁",
    "ru": "Сохранить рядом с видео с тем же именем файла",
    "pl": "Zapisz obok wideo z tą samą nazwą",
    "uk": "Зберегти поруч з відео з тим же ім'ям",
    "ja": "同じファイル名で動画の横に保存",
    "ko": "동일한 파일명으로 비디오 옆에 저장",
    "hi": "समान फ़ाइल नाम के साथ वीडियो के पास सहेजें"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_TO_DESKTOP = {
    "en": "Save to Desktop",
    "es": "Guardar en el escritorio",
    "tr": "Masaüstüne kaydet",
    "zh": "保存到桌面",
    "ru": "Сохранить на рабочем столе",
    "pl": "Zapisz na pulpicie",
    "uk": "Зберегти на робочому столі",
    "ja": "デスクトップに保存",
    "ko": "바탕 화면에 저장",
    "hi": "डेस्कटॉप पर सहेजें"
}
# TEXT SHOULD BE SHORT
OPTION_REPLACE_ORIGINAL_SUBTITLE = {
    "en": "Overwrite input subtitle",
    "es": "Sobrescribir subtítulo de entrada",
    "tr": "Girdi altyazının üzerine yaz",
    "zh": "覆盖输入字幕",
    "ru": "Перезаписать входные субтитры",
    "pl": "Nadpisz napisy wejściowe",
    "uk": "Перезаписати вхідні субтитри",
    "ja": "入力字幕を上書き",
    "ko": "입력 자막 덮어쓰기",
    "hi": "इनपुट उपशीर्षक अधिलेखित करें"
}
# TEXT SHOULD BE SHORT
OPTION_SELECT_DESTINATION_FOLDER = {
    "en": "Select destination folder",
    "es": "Seleccionar carpeta de destino",
    "tr": "Hedef klasörü seç",
    "zh": "选择目标文件夹",
    "ru": "Выберите папку назначения",
    "pl": "Wybierz folder docelowy",
    "uk": "Виберіть папку призначення",
    "ja": "保存先フォルダを選択",
    "ko": "대상 폴더 선택",
    "hi": "गंतव्य फ़ोल्डर चुनें"
}
CHECKBOX_NO_FIX_FRAMERATE = {
    "en": "Don't fix framerate",
    "es": "No corregir la velocidad de fotogramas",
    "tr": "Kare hızını düzeltme",
    "zh": "不修复帧速率",
    "ru": "Не исправлять частоту кадров",
    "pl": "Nie naprawiaj częstotliwości klatek",
    "uk": "Не виправляти частоту кадрів",
    "ja": "フレームレートを修正しない",
    "ko": "프레임 속도 수정 안 함",
    "hi": "फ्रेमरेट ठीक न करें"
}
CHECKBOX_GSS = {
    "en": "Use golden-section search",
    "es": "Usar búsqueda de sección áurea",
    "tr": "Altın oran aramasını kullan",
    "zh": "使用黄金分割搜索",
    "ru": "Использовать поиск золотого сечения",
    "pl": "Użyj wyszukiwania złotego podziału",
    "uk": "Використовувати пошук золотого перетину",
    "ja": "黄金分割探索を使用",
    "ko": "황금 분할 검색 사용",
    "hi": "स्वर्ण-खंड खोज का उपयोग करें"
}
CHECKBOX_VAD = {
    "en": "Use auditok instead of WebRTC's VAD",
    "es": "Usar auditok en lugar del VAD de WebRTC",
    "tr": "WebRTC'nin VAD'si yerine auditok kullan",
    "zh": "使用 auditok 而不是 WebRTC 的 VAD",
    "ru": "Использовать auditok вместо VAD WebRTC",
    "pl": "Użyj auditok zamiast VAD WebRTC",
    "uk": "Використовувати auditok замість VAD WebRTC",
    "ja": "WebRTCのVADの代わりにauditokを使用",
    "ko": "WebRTC의 VAD 대신 auditok 사용",
    "hi": "WebRTC के VAD के बजाय auditok का उपयोग करें"
}
# TEXT SHOULD BE SHORT
LABEL_SPLIT_PENALTY = {
    "en": "Split Penalty (Default: 7, Recommended: 5-20, No splits: 0)",
    "es": "Penalización (Predeterminado: 7, Recomendado: 5-20, Sin div: 0)",
    "tr": "Bölme Cezası (Varsayılan: 7, Önerilen: 5-20, Bölme yok: 0)",
    "zh": "分割惩罚（默认：7，推荐：5-20，无分割：0）",
    "ru": "Штраф (По умолчанию: 7, Рекомендуется: 5-20, Без: 0)",
    "pl": "Kara za podział (Domyślnie: 7, Zalecane: 5-20, Bez: 0)",
    "uk": "Штраф (За замовч.: 7, Рекоменд.: 5-20, Без: 0)",
    "ja": "分割ペナルティ (既定: 7, 推奨: 5-20, 分割なし: 0)",
    "ko": "분할 페널티 (기본값: 7, 권장: 5-20, 분할 없음: 0)",
    "hi": "विभाजन पेनल्टी (डिफ़ॉल्ट: 7, अनुशंसित: 5-20, कोई नहीं: 0)"
}
PAIR_FILES_TITLE = {
    "en": "Pair Files",
    "es": "Emparejar archivos",
    "tr": "Dosyaları Eşleştir",
    "zh": "配对文件",
    "ru": "Сопоставить файлы",
    "pl": "Paruj Pliki",
    "uk": "З'єднати Файли",
    "ja": "ファイルをペアにする",
    "ko": "파일 페어링",
    "hi": "फ़ाइलें जोड़ें"
}
PAIR_FILES_MESSAGE = {
    "en": "The subtitle and video have different filenames. Do you want to pair them?",
    "es": "El subtítulo y el video tienen nombres de archivo diferentes. ¿Quieres emparejarlos?",
    "tr": "Altyazı ve video farklı dosya adlarına sahip. Eşleştirmek istiyor musunuz?",
    "zh": "字幕和视频的文件名不同。您要配对它们吗？",
    "ru": "У субтитров и видео разные имена файлов. Хотите ли вы их сопоставить?",
    "pl": "Napisy i wideo mają różne nazwy plików. Czy chcesz je sparować?",
    "uk": "Субтитри та відео мають різні імена файлів. Бажаєте їх з'єднати?",
    "ja": "字幕と動画のファイル名が異なります。ペアにしますか？",
    "ko": "자막과 비디오의 파일 이름이 다릅니다. 페어링하시겠습니까?",
    "hi": "उपशीर्षक और वीडियो के फ़ाइल नाम अलग हैं। क्या आप उन्हें जोड़ना चाहते हैं?"
}
UNPAIRED_SUBTITLES_TITLE = {
    "en": "Unpaired Subtitles",
    "es": "Subtítulos no emparejados",
    "tr": "Eşleşmemiş Altyazılar",
    "zh": "未配对的字幕",
    "ru": "Несопоставленные субтитры",
    "pl": "Niesparowane Napisy",
    "uk": "Непоєднані Субтитри",
    "ja": "未ペアの字幕",
    "ko": "페어링되지 않은 자막",
    "hi": "अजुड़े उपशीर्षक"
}
UNPAIRED_SUBTITLES_MESSAGE = {
    "en": "There are {unpaired_count} unpaired subtitle(s). Do you want to add them as subtitles with [no video/reference subtitle] tag?",
    "es": "Hay {unpaired_count} subtítulo(s) no emparejado(s). ¿Quieres agregarlos como subtítulos con la etiqueta [sin video/subtítulo de referencia]?",
    "tr": "{unpaired_count} eşleşmemiş altyazı var. Bunları [video/referans altyazı yok] etiketiyle altyazı olarak eklemek istiyor musunuz?",
    "zh": "有 {unpaired_count} 个未配对的字幕。您要将它们添加为带有 [无视频/参考字幕] 标签的字幕吗？",
    "ru": "Есть {unpaired_count} несопоставленный(ые) субтитр(ы). Хотите добавить их как субтитры с тегом [нет видео/справочных субтитров]?",
    "pl": "Jest {unpaired_count} niesparowanych napisów. Czy chcesz dodać je jako napisy z tagiem [brak wideo/napisów referencyjnych]?",
    "uk": "Є {unpaired_count} непоєднаних субтитрів. Бажаєте додати їх як субтитри з тегом [без відео/довідкових субтитрів]?",
    "ja": "{unpaired_count}個の未ペアの字幕があります。[動画/参照字幕なし]タグ付きで追加しますか？",
    "ko": "페어링되지 않은 자막이 {unpaired_count}개 있습니다. [비디오/참조 자막 없음] 태그로 추가하시겠습니까?",
    "hi": "{unpaired_count} अजुड़े उपशीर्षक हैं। क्या आप उन्हें [कोई वीडियो/संदर्भ उपशीर्षक नहीं] टैग के साथ जोड़ना चाहते हैं?"
}
NO_VIDEO = {
    "en": "[no video/reference subtitle]",
    "es": "[sin video/subtítulo de referencia]",
    "tr": "[video/referans altyazı yok]",
    "zh": "[无视频/参考字幕]",
    "ru": "[нет видео/справочных субтитров]",
    "pl": "[brak wideo/napisów referencyjnych]",
    "uk": "[без відео/довідкових субтитрів]",
    "ja": "[動画/参照字幕なし]",
    "ko": "[비디오/참조 자막 없음]",
    "hi": "[कोई वीडियो/संदर्भ उपशीर्षक नहीं]"
}
NO_SUBTITLE = {
    "en": "[no subtitle]",
    "es": "[sin subtítulo]",
    "tr": "[altyazı yok]",
    "zh": "[没有字幕]",
    "ru": "[нет субтитров]",
    "pl": "[brak napisów]",
    "uk": "[без субтитрів]",
    "ja": "[字幕なし]",
    "ko": "[자막 없음]",
    "hi": "[कोई उपशीर्षक नहीं]"
}
VIDEO_OR_SUBTITLE_TEXT = {
    "en": "Video or subtitle",
    "es": "Video o subtítulo",
    "tr": "Video veya altyazı",
    "zh": "视频或字幕",
    "ru": "Видео или субтитры",
    "pl": "Wideo lub napisy",
    "uk": "Відео або субтитри",
    "ja": "動画または字幕",
    "ko": "비디오 또는 자막",
    "hi": "वीडियो या उपशीर्षक"
}
VIDEO_INPUT_LABEL = {
    "en": "Video/Reference subtitle",
    "es": "Video/Subtítulo de referencia",
    "tr": "Video/Referans altyazı",
    "zh": "视频/参考字幕",
    "ru": "Видео/Справочные субтитры",
    "pl": "Wideo/Napisy referencyjne",
    "uk": "Відео/Довідкові субтитри",
    "ja": "動画/参照字幕",
    "ko": "비디오/참조 자막",
    "hi": "वीडियो/संदर्भ उपशीर्षक"
}
SUBTITLE_INPUT_LABEL = {
    "en": "Input Subtitle",
    "es": "Subtítulo de entrada",
    "tr": "Girdi Altyazı",
    "zh": "输入字幕",
    "ru": "Входные субтитры",
    "pl": "Napisy wejściowe",
    "uk": "Вхідні субтитри",
    "ja": "入力字幕",
    "ko": "입력 자막",
    "hi": "इनपुट उपशीर्षक"
}
SUBTITLE_FILES_TEXT = {
    "en": "Subtitle files",
    "es": "Archivos de subtítulos",
    "tr": "Altyazı dosyaları",
    "zh": "字幕文件",
    "ru": "Файлы субтитров",
    "pl": "Pliki napisów",
    "uk": "Файли субтитрів",
    "ja": "字幕ファイル",
    "ko": "자막 파일",
    "hi": "उपशीर्षक फ़ाइलें"
}
CONTEXT_MENU_REMOVE = {
    "en": "Remove",
    "es": "Eliminar",
    "tr": "Kaldır",
    "zh": "删除",
    "ru": "Удалить",
    "pl": "Usuń",
    "uk": "Видалити",
    "ja": "削除",
    "ko": "제거",
    "hi": "हटाएं"
}
CONTEXT_MENU_CHANGE = {
    "en": "Change",
    "es": "Cambiar",
    "tr": "Değiştir",
    "zh": "更改",
    "ru": "Изменить",
    "pl": "Zmień",
    "uk": "Змінити",
    "ja": "変更",
    "ko": "변경",
    "hi": "बदलें"
}
CONTEXT_MENU_ADD_PAIR = {
    "en": "Add Pair",
    "es": "Agregar par",
    "tr": "Çift Ekle",
    "zh": "添加配对",
    "ru": "Добавить пару",
    "pl": "Dodaj Parę",
    "uk": "Додати Пару",
    "ja": "ペアを追加",
    "ko": "페어 추가",
    "hi": "जोड़ा जोड़ें"
}
CONTEXT_MENU_CLEAR_ALL = {
    "en": "Clear All",
    "es": "Limpiar todo",
    "tr": "Hepsini Temizle",
    "zh": "清除所有",
    "ru": "Очистить все",
    "pl": "Wyczyść Wszystko",
    "uk": "Очистити Все",
    "ja": "すべてクリア",
    "ko": "모두 지우기",
    "hi": "सभी साफ करें"
}
CONTEXT_MENU_SHOW_PATH = {
    "en": "Show path",
    "es": "Mostrar ruta",
    "tr": "Yolu göster",
    "zh": "显示路径",
    "ru": "Показать путь",
    "pl": "Pokaż ścieżkę",
    "uk": "Показати шлях",
    "ja": "パスを表示",
    "ko": "경로 표시",
    "hi": "पथ दिखाएं"
}
BUTTON_ADD_FILES = {
    "en": "Add files",
    "es": "Agregar archivos",
    "tr": "Dosya ekle",
    "zh": "添加文件",
    "ru": "Добавить файлы",
    "pl": "Dodaj pliki",
    "uk": "Додати файли",
    "ja": "ファイルを追加",
    "ko": "파일 추가",
    "hi": "फ़ाइलें जोड़ें"
}
MENU_ADD_FOLDER = {
    "en": "Add Folder",
    "es": "Agregar carpeta",
    "tr": "Klasör ekle",
    "zh": "添加文件夹",
    "ru": "Добавить папку",
    "pl": "Dodaj Folder",
    "uk": "Додати Папку",
    "ja": "フォルダを追加",
    "ko": "폴더 추가",
    "hi": "फ़ोल्डर जोड़ें"
}
MENU_ADD_MULTIPLE_FILES = {
    "en": "Add Multiple Files",
    "es": "Agregar múltiples archivos",
    "tr": "Çoklu Dosya Ekle",
    "zh": "添加多个文件",
    "ru": "Добавить несколько файлов",
    "pl": "Dodaj Wiele Plików",
    "uk": "Додати Кілька Файлів",
    "ja": "複数のファイルを追加",
    "ko": "여러 파일 추가",
    "hi": "कई फ़ाइलें जोड़ें"
}
MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS = {
    "en": "Auto-Pairing with Season/Episode",
    "es": "Emparejamiento automático por Temporada/Episodio",
    "tr": "Sezon/Bölüm ile Otomatik Eşleme",
    "zh": "按季/集自动配对",
    "ru": "Автоматическое сопоставление по сезону/эпизоду",
    "pl": "Automatyczne parowanie według Sezonu/Odcinka",
    "uk": "Автоматичне з'єднання за Сезоном/Епізодом",
    "ja": "シーズン/エピソードによる自動ペアリング",
    "ko": "시즌/에피소드로 자동 페어링",
    "hi": "सीजन/एपिसोड के साथ स्वचालित-जोड़ी"
}
ALASS_SPEED_OPTIMIZATION_TEXT = {
    "en": "Disable speed optimization",
    "es": "Deshabilitar optimización de velocidad",
    "tr": "Hız optimizasyonunu devre dışı bırak",
    "zh": "禁用速度优化",
    "ru": "Отключить оптимизацию скорости",
    "pl": "Wyłącz optymalizację prędkości",
    "uk": "Вимкнути оптимізацію швидкості",
    "ja": "速度最適化を無効化",
    "ko": "속도 최적화 비활성화",
    "hi": "गति अनुकूलन अक्षम करें"
}
ALASS_DISABLE_FPS_GUESSING_TEXT = {
    "en": "Disable FPS guessing",
    "es": "Deshabilitar adivinación de FPS",
    "tr": "FPS tahminini devre dışı bırak",
    "zh": "禁用 FPS 猜测",
    "ru": "Отключить догадку FPS",
    "pl": "Wyłącz wykrywanie FPS",
    "uk": "Вимкнути визначення FPS",
    "ja": "FPS推測を無効化",
    "ko": "FPS 추측 비활성화",
    "hi": "FPS अनुमान अक्षम करें"
}
REF_DROP_TEXT = {
    "en": "Drop videos or reference subtitles here\nor click to browse.",
    "es": "Suelta videos o subtítulos de referencia aquí\no haz clic para buscar.",
    "tr": "Videoları veya referans altyazıları buraya sürükleyip bırakın\nveya göz atmak için tıklayın.",
    "zh": "将视频或参考字幕拖放到此处\n或点击浏览。",
    "ru": "Перетащите видео или справочные субтитры сюда\nили нажмите, чтобы выбрать.",
    "pl": "Upuść filmy lub napisy referencyjne tutaj\nlub kliknij, aby przeglądać.",
    "uk": "Перетягніть відео або довідкові субтитри сюди\nабо натисніть для вибору.",
    "ja": "動画または参照字幕をここにドロップ\nまたはクリックして参照。",
    "ko": "비디오나 참조 자막을 여기에 끌어다 놓거나\n클릭하여 찾아보세요.",
    "hi": "वीडियो या संदर्भ उपशीर्षक यहाँ खींचें\nया ब्राउज़ करने के लिए क्लिक करें।"
}
SUB_DROP_TEXT = {
    "en": "Drag and drop subtitles here\nor click to browse.",
    "es": "Arrastre y suelte subtítulos aquí\no haga clic para buscar.",
    "tr": "Altyazıları buraya sürükleyip bırakın\nveya göz atmak için tıklayın.",
    "zh": "将字幕拖放到此处\n或点击浏览。",
    "ru": "Перетащите сюда субтитры\nили нажмите, чтобы выбрать.",
    "pl": "Upuść napisy tutaj\nlub kliknij, aby przeglądać.",
    "uk": "Перетягніть субтитри сюди\nабо натисніть для вибору.",
    "ja": "字幕をここにドロップ\nまたはクリックして参照。",
    "ko": "자막을 여기에 끌어다 놓거나\n클릭하여 찾아보세요.",
    "hi": "उपशीर्षक यहाँ खींचें\nया ब्राउज़ करने के लिए क्लिक करें।"
}
REF_LABEL_TEXT = {
    "en": "Videos/Reference Subtitles",
    "es": "Videos/Subtítulos de referencia",
    "tr": "Videolar/Referans Altyazılar", 
    "zh": "视频/参考字幕",
    "ru": "Видео/Справочные субтитры",
    "pl": "Wideo/Napisy referencyjne",
    "uk": "Відео/Довідкові субтитри",
    "ja": "動画/参照字幕",
    "ko": "비디오/참조 자막",
    "hi": "वीडियो/संदर्भ उपशीर्षक"
}
SUB_LABEL_TEXT = {
    "en": "Input Subtitles",
    "es": "Subtítulos de entrada",
    "tr": "Girdi Altyazılar",
    "zh": "输入字幕",
    "ru": "Входные субтитры",
    "pl": "Napisy wejściowe",
    "uk": "Вхідні субтитри",
    "ja": "入力字幕",
    "ko": "입력 자막",
    "hi": "इनपुट उपशीर्षक"
}
PROCESS_PAIRS = {
    "en": "Add Pairs",
    "es": "Agregar pares",
    "tr": "Çiftleri Ekle",
    "zh": "添加配对",
    "ru": "Добавить пары",
    "pl": "Dodaj Pary",
    "uk": "Додати Пари",
    "ja": "ペアを追加",
    "ko": "페어 추가",
    "hi": "जोड़ियाँ जोड़ें"
}
# TEXT SHOULD BE SHORT
SYNC_TOOL_LABEL_TEXT = {
    "en": "Sync using",
    "es": "Sincr. con",
    "tr": "Senkr. aracı",
    "zh": "使用同步工具",
    "ru": "Синхр. с",
    "pl": "Synch. przez",
    "uk": "Синх. через",
    "ja": "同期ツール",
    "ko": "동기화 도구",
    "hi": "सिंक टूल"
}
EXPLANATION_TEXT_IN_REFERENCE__SUBTITLE_PARIRING = {
    "en": """How the Pairing Works?
    """+PROGRAM_NAME+""" will automatically match videos or reference subtitles with subtitle files using similar names.
    For example: "S01E01.srt/mkv" will be paired with "1x01.srt"
    Supported combinations: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "es": """¿Cómo funciona el emparejamiento?
    """+PROGRAM_NAME+""" emparejará automáticamente los videos o subtítulos de referencia con los archivos de subtítulos usando nombres similares.
    Por ejemplo: "S01E01.srt/mkv" se emparejará con "1x01.srt"
    Combinaciones compatibles: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "tr": """Eşleştirme Nasıl Çalışır?
    """+PROGRAM_NAME+""" benzer isimlere sahip videoları veya referans altyazıları hedef altyazı dosyaları ile otomatik olarak eşleştirecektir.
    Örneğin: "S01E01.srt/mkv" ile "1x01.srt" eşleştirilecektir.
    Desteklenen kombinasyonlar: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "zh": """配对如何工作？
    """+PROGRAM_NAME+""" 将自动匹配具有相似名称的视频或参考字幕与字幕文件。
    例如："S01E01.srt/mkv" 将与 "1x01.srt" 配对
    支持的组合：S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "ru": """Как работает сопоставление?
    """+PROGRAM_NAME+""" автоматически сопоставит видео или справочные субтитры с файлами субтитров, используя похожие имена.
    Например: "S01E01.srt/mkv" будет сопоставлен с "1x01.srt"
    Поддерживаемые комбинации: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "pl": """Jak działa parowanie?
    """+PROGRAM_NAME+""" automatycznie dopasuje filmy lub napisy referencyjne do plików napisów, używając podobnych nazw.
    Na przykład: "S01E01.srt/mkv" zostanie sparowany z "1x01.srt"
    Wspierane kombinacje: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "uk": """Як працює з'єднання?
    """+PROGRAM_NAME+""" автоматично зіставить відео або довідкові субтитри з файлами субтитрів, використовуючи схожі імена.
    Наприклад: "S01E01.srt/mkv" буде з'єднано з "1x01.srt"
    Підтримувані комбінації: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "ja": """ペアリングの仕組みは？
    """+PROGRAM_NAME+"""は類似した名前を使用して、動画または参照字幕を字幕ファイルと自動的にマッチングします。
    例：「S01E01.srt/mkv」は「1x01.srt」とペアになります
    サポートされる組み合わせ：S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "ko": """페어링은 어떻게 작동하나요?
    """+PROGRAM_NAME+"""는 유사한 이름을 사용하여 비디오 또는 참조 자막을 자막 파일과 자동으로 매칭합니다.
    예: "S01E01.srt/mkv"는 "1x01.srt"와 페어링됩니다
    지원되는 조합: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101""",
    "hi": """जोड़ी कैसे काम करती है?
    """+PROGRAM_NAME+""" समान नामों का उपयोग करके वीडियो या संदर्भ उपशीर्षक को उपशीर्षक फ़ाइलों के साथ स्वचालित रूप से मिलान करेगा।
    उदाहरण: "S01E01.srt/mkv" को "1x01.srt" के साथ जोड़ा जाएगा
    समर्थित संयोजन: S01E01, S1E1, S01E1, S1E01, S01B01, S1B1, S01B1, S1B01, 1x01, 01x1, 01x01, 1x1, 101"""
}
THEME_TEXT = {
    "en": "Theme",
    "es": "Tema",
    "tr": "Tema",
    "zh": "主题",
    "ru": "Тема",
    "pl": "Motyw",
    "uk": "Тема",
    "ja": "テーマ",
    "ko": "테마",
    "hi": "थीम"
}
THEME_SYSTEM_TEXT = {
    "en": "System",
    "es": "Sistema",
    "tr": "Sistem",
    "zh": "系统",
    "ru": "Система",
    "pl": "Systemowy",
    "uk": "Системна",
    "ja": "システム",
    "ko": "시스템",
    "hi": "सिस्टम"
}
THEME_DARK_TEXT = {
    "en": "Dark",
    "es": "Oscuro",
    "tr": "Koyu",
    "zh": "暗",
    "ru": "Темный",
    "pl": "Ciemny",
    "uk": "Темна",
    "ja": "ダーク",
    "ko": "다크",
    "hi": "डार्क"
}
THEME_LIGHT_TEXT = {
    "en": "Light",
    "es": "Claro",
    "tr": "Açık",
    "zh": "亮",
    "ru": "Светлый",
    "pl": "Jasny",
    "uk": "Світла",
    "ja": "ライト",
    "ko": "라이트",
    "hi": "लाइट"
}
SUCCESS_LOG_TEXT = {
    "en": "Success! Subtitle shifted by {milliseconds} milliseconds and saved to: {new_subtitle_file}",
    "es": "¡Éxito! Subtítulo desplazado por {milliseconds} milisegundos y guardado en: {new_subtitle_file}",
    "tr": "Başarılı! Altyazı {milliseconds} milisaniye kaydırıldı ve kaydedildi: {new_subtitle_file}",
    "zh": "成功！字幕移位 {milliseconds} 毫秒，并保存到：{new_subtitle_file}",
    "ru": "Успех! Субтитры сдвинуты на {milliseconds} миллисекунд и сохранены в: {new_subtitle_file}",
    "pl": "Sukces! Napisy przesunięte o {milliseconds} milisekund i zapisane do: {new_subtitle_file}",
    "uk": "Успіх! Субтитри зсунуто на {milliseconds} мілісекунд і збережено до: {new_subtitle_file}",
    "ja": "成功！字幕を{milliseconds}ミリ秒シフトし、保存先：{new_subtitle_file}",
    "ko": "성공! 자막이 {milliseconds}밀리초 이동되어 저장됨: {new_subtitle_file}",
    "hi": "सफल! उपशीर्षक {milliseconds} मिलीसेकंड शिफ्ट किया गया और यहाँ सहेजा गया: {new_subtitle_file}"
}
SYNC_SUCCESS_MESSAGE = {
    "en": "Success! Synchronized subtitle saved to: {output_subtitle_file}",
    "es": "¡Éxito! Subtítulo sincronizado guardado en: {output_subtitle_file}",
    "tr": "Başarılı! Senkronize edilmiş altyazı kaydedildi: {output_subtitle_file}",
    "zh": "成功！同步字幕保存到：{output_subtitle_file}",
    "ru": "Успех! Синхронизированные субтитры сохранены в: {output_subtitle_file}",
    "pl": "Sukces! Zsynchronizowane napisy zapisane do: {output_subtitle_file}",
    "uk": "Успіх! Синхронізовані субтитри збережено до: {output_subtitle_file}",
    "ja": "成功！同期した字幕の保存先：{output_subtitle_file}",
    "ko": "성공! 동기화된 자막 저장됨: {output_subtitle_file}",
    "hi": "सफल! सिंक्रनाइज़ किया गया उपशीर्षक यहाँ सहेजा गया: {output_subtitle_file}"
}
ERROR_SAVING_SUBTITLE = {
    "en": "Error saving subtitle file: {error_message}",
    "es": "Error al guardar el archivo de subtítulos: {error_message}",
    "tr": "Altyazı dosyası kaydedilirken hata: {error_message}",
    "zh": "保存字幕文件时出错：{error_message}",
    "ru": "Ошибка сохранения файла субтитров: {error_message}",
    "pl": "Błąd podczas zapisywania pliku napisów: {error_message}",
    "uk": "Помилка збереження файлу субтитрів: {error_message}",
    "ja": "字幕ファイルの保存エラー：{error_message}",
    "ko": "자막 파일 저장 오류: {error_message}",
    "hi": "उपशीर्षक फ़ाइल सहेजने में त्रुटि: {error_message}"
}
NON_ZERO_MILLISECONDS = {
    "en": "Please enter a non-zero value for milliseconds.",
    "es": "Por favor, ingrese un valor distinto de cero para milisegundos.",
    "tr": "Lütfen milisaniye için sıfır olmayan bir değer girin.",
    "zh": "请输入非零毫秒值。",
    "ru": "Пожалуйста, введите ненулевое значение для миллисекунд.",
    "pl": "Proszę wprowadzić niezerową wartość milisekund.",
    "uk": "Будь ласка, введіть ненульове значення мілісекунд.",
    "ja": "ミリ秒にゼロ以外の値を入力してください。",
    "ko": "0이 아닌 밀리초 값을 입력하세요.",
    "hi": "कृपया मिलीसेकंड के लिए शून्य से अलग मान दर्ज करें।"
}
SELECT_ONLY_ONE_OPTION = {
    "en": "Please select only one option: Save to Desktop or Replace Input Subtitle.",
    "es": "Por favor, seleccione solo una opción: Guardar en el escritorio o Reemplazar el subtítulo de entrada.",
    "tr": "Lütfen yalnızca bir seçenek seçin: Masaüstüne kaydet veya Girdi altyazıyı değiştir.",
    "zh": "请只选择一个选项：保存到桌面或替换输入字幕。",
    "ru": "Пожалуйста, выберите только один вариант: Сохранить на рабочий стол или Заменить входные субтитры.",
    "pl": "Proszę wybrać tylko jedną opcję: Zapisz na pulpicie lub Zastąp wejściowe napisy.",
    "uk": "Будь ласка, виберіть лише один варіант: Зберегти на робочий стіл або Замінити вхідні субтитри.",
    "ja": "デスクトップに保存か入力字幕を置き換えるか、どちらか一つを選択してください。",
    "ko": "바탕 화면에 저장 또는 입력 자막 교체 중 하나만 선택하세요.",
    "hi": "कृपया एक ही विकल्प चुनें: डेस्कटॉप पर सहेजें या इनपुट उपशीर्षक बदलें।"
}
VALID_NUMBER_MILLISECONDS = {
    "en": "Please enter a valid number of milliseconds.",
    "es": "Por favor, ingrese un número válido de milisegundos.",
    "tr": "Lütfen geçerli bir milisaniye sayısı girin.",
    "zh": "请输入有效的毫秒数。",
    "ru": "Пожалуйста, введите допустимое количество миллисекунд.",
    "pl": "Proszę wprowadzić prawidłową liczbę milisekund.",
    "uk": "Будь ласка, введіть дійсну кількість мілісекунд.",
    "ja": "有効なミリ秒数を入力してください。",
    "ko": "유효한 밀리초 수를 입력하세요.",
    "hi": "कृपया मिलीसेकंड की एक मान्य संख्या दर्ज करें।"
}
SELECT_SUBTITLE = {
    "en": "Please select a subtitle file.",
    "es": "Por favor, seleccione un archivo de subtítulos.",
    "tr": "Lütfen bir altyazı dosyası seçin.",
    "zh": "请选择一个字幕文件。",
    "ru": "Пожалуйста, выберите файл субтитров.",
    "pl": "Proszę wybrać plik napisów.",
    "uk": "Будь ласка, виберіть файл субтитрів.",
    "ja": "字幕ファイルを選択してください。",
    "ko": "자막 파일을 선택하세요.",
    "hi": "कृपया एक उपशीर्षक फ़ाइल चुनें।"
}
SELECT_VIDEO = {
    "en": "Please select a video file.",
    "es": "Por favor, seleccione un archivo de video.",
    "tr": "Lütfen bir video dosyası seçin.",
    "zh": "请选择一个视频文件。",
    "ru": "Пожалуйста, выберите файл видео.",
    "pl": "Proszę wybrać plik wideo.",
    "uk": "Будь ласка, виберіть файл відео.",
    "ja": "動画ファイルを選択してください。",
    "ko": "비디오 파일을 선택하세요.",
    "hi": "कृपया एक वीडियो फ़ाइल चुनें।"
}
SELECT_VIDEO_OR_SUBTITLE = {
    "en": "Please select a video or reference subtitle.",
    "es": "Por favor, seleccione un video o subtítulo de referencia.",
    "tr": "Lütfen bir video veya referans altyazı seçin.",
    "zh": "请选择一个视频或参考字幕。",
    "ru": "Пожалуйста, выберите видео или справочные субтитры.",
    "pl": "Proszę wybrać plik wideo lub napisy referencyjne.",
    "uk": "Будь ласка, виберіть відео або довідкові субтитри.",
    "ja": "動画または参照字幕を選択してください。",
    "ko": "비디오 또는 참조 자막을 선택하세요.",
    "hi": "कृपया एक वीडियो या संदर्भ उपशीर्षक चुनें।"
}
DROP_VIDEO_SUBTITLE_PAIR = {
    "en": "Please drop a video, subtitle or pair.",
    "es": "Por favor, suelte un video, subtítulo o par.",
    "tr": "Lütfen bir video, altyazı veya çift bırakın.",
    "zh": "请拖放一个视频、字幕或配对。",
    "ru": "Пожалуйста, перетащите видео, субтитры или пару.",
    "pl": "Proszę upuścić wideo, napisy lub parę.",
    "uk": "Будь ласка, перетягніть відео, субтитри або пару.",
    "ja": "動画、字幕、またはペアをドロップしてください。",
    "ko": "비디오, 자막 또는 페어를 드롭하세요.",
    "hi": "कृपया एक वीडियो, उपशीर्षक या जोड़ी छोड़ें।"
}
DROP_VIDEO_OR_SUBTITLE = {
    "en": "Please drop a video or reference subtitle file.",
    "es": "Por favor, suelte un archivo de video o subtítulo de referencia.",
    "tr": "Lütfen bir video veya referans altyazı dosyası bırakın.",
    "zh": "请拖放一个视频或参考字幕文件。",
    "ru": "Пожалуйста, перетащите видео или файл справочных субтитров.",
    "pl": "Proszę upuścić plik wideo lub napisy referencyjne.",
    "uk": "Будь ласка, перетягніть відео або файл довідкових субтитрів.",
    "ja": "動画または参照字幕ファイルをドロップしてください。",
    "ko": "비디오 또는 참조 자막 파일을 드롭하세요.",
    "hi": "कृपया एक वीडियो या संदर्भ उपशीर्षक फ़ाइल छोड़ें।"
}
DROP_SUBTITLE_FILE = {
    "en": "Please drop a subtitle file.",
    "es": "Por favor, suelte un archivo de subtítulos.",
    "tr": "Lütfen bir altyazı dosyası bırakın.",
    "zh": "请拖放一个字幕文件。",
    "ru": "Пожалуйста, перетащите файл субтитров.",
    "pl": "Proszę upuścić plik napisów.",
    "uk": "Будь ласка, перетягніть файл субтитрів.",
    "ja": "字幕ファイルをドロップしてください。",
    "ko": "자막 파일을 드롭하세요.",
    "hi": "कृपया एक उपशीर्षक फ़ाइल छोड़ें।"
}
DROP_SINGLE_SUBTITLE_FILE = {
    "en": "Please drop a single subtitle file.",
    "es": "Por favor, suelte un solo archivo de subtítulos.",
    "tr": "Lütfen tek bir altyazı dosyası bırakın.",
    "zh": "请拖放一个单独的字幕文件。",
    "ru": "Пожалуйста, перетащите один файл субтитров.",
    "pl": "Proszę upuścić jeden plik napisów.",
    "uk": "Будь ласка, перетягніть один файл субтитрів.",
    "ja": "単一の字幕ファイルをドロップしてください。",
    "ko": "단일 자막 파일을 드롭하세요.",
    "hi": "कृपया एकल उपशीर्षक फ़ाइल छोड़ें।"
}
DROP_SINGLE_SUBTITLE_PAIR = {
    "en": "Please drop a single subtitle or pair.",
    "es": "Por favor, suelte un solo subtítulo o par.",
    "tr": "Lütfen tek bir altyazı veya çift bırakın.",
    "zh": "请拖放一个单独的字幕或配对。",
    "ru": "Пожалуйста, перетащите один субтитр или пару.",
    "pl": "Proszę upuścić jeden napis lub parę.",
    "uk": "Будь ласка, перетягніть один субтитр або пару.",
    "ja": "単一の字幕またはペアをドロップしてください。",
    "ko": "단일 자막 또는 페어를 드롭하세요.",
    "hi": "कृपया एकल उपशीर्षक या जोड़ी छोड़ें।"
}
SELECT_BOTH_FILES = {
    "en": "Please select both video/reference subtitle and subtitle file.",
    "es": "Por favor, seleccione tanto el archivo de video/subtítulo de referencia como el archivo de subtítulos.",
    "tr": "Lütfen hem video/referans altyazı hem de altyazı dosyasını seçin.",
    "zh": "请选择视频/参考字幕和字幕文件。",
    "ru": "Пожалуйста, выберите как видео/справочный субтитр, так и файл субтитров.",
    "pl": "Proszę wybrać zarówno plik wideo/napisy referencyjne, jak i plik napisów.",
    "uk": "Будь ласка, виберіть як відео/довідкові субтитри, так і файл субтитрів.",
    "ja": "動画/参照字幕と字幕ファイルの両方を選択してください。",
    "ko": "비디오/참조 자막 및 자막 파일을 모두 선택하세요.",
    "hi": "कृपया वीडियो/संदर्भ उपशीर्षक और उपशीर्षक फ़ाइल दोनों चुनें।"
}
SELECT_DIFFERENT_FILES = {
    "en": "Please select different subtitle files.",
    "es": "Por favor, seleccione diferentes archivos de subtítulos.",
    "tr": "Lütfen farklı altyazı dosyaları seçin.",
    "zh": "请选择不同的字幕文件。",
    "ru": "Пожалуйста, выберите разные файлы субтитров.",
    "pl": "Proszę wybrać różne pliki napisów.",
    "uk": "Будь ласка, виберіть різні файли субтитрів.",
    "ja": "異なる字幕ファイルを選択してください。",
    "ko": "다른 자막 파일을 선택하세요.",
    "hi": "कृपया विभिन्न उपशीर्षक फ़ाइलें चुनें।"
}
SUBTITLE_FILE_NOT_EXIST = {
    "en": "Subtitle file does not exist.",
    "es": "El archivo de subtítulos no existe.",
    "tr": "Altyazı dosyası mevcut değil.",
    "zh": "字幕文件不存在。",
    "ru": "Файл субтитров не существует.",
    "pl": "Plik napisów nie istnieje.",
    "uk": "Файл субтитрів не існує.",
    "ja": "字幕ファイルが存在しません。",
    "ko": "자막 파일이 존재하지 않습니다.",
    "hi": "उपशीर्षक फ़ाइल मौजूद नहीं है।"
}
VIDEO_FILE_NOT_EXIST = {
    "en": "Video file does not exist.",
    "es": "El archivo de video no existe.",
    "tr": "Video dosyası mevcut değil.",
    "zh": "视频文件不存在。",
    "ru": "Файл видео не существует.",
    "pl": "Plik wideo nie istnieje.",
    "uk": "Файл відео не існує.",
    "ja": "動画ファイルが存在しません。",
    "ko": "비디오 파일이 존재하지 않습니다.",
    "hi": "वीडियो फ़ाइल मौजूद नहीं है।"
}
ERROR_LOADING_SUBTITLE = {
    "en": "Error loading subtitle file: {error_message}",
    "es": "Error al cargar el archivo de subtítulos: {error_message}",
    "tr": "Altyazı dosyası yüklenirken hata: {error_message}",
    "zh": "加载字幕文件时出错：{error_message}",
    "ru": "Ошибка загрузки файла субтитров: {error_message}",
    "pl": "Błąd ładowania pliku napisów: {error_message}",
    "uk": "Помилка завантаження файлу субтитрів: {error_message}",
    "ja": "字幕ファイルの読み込みエラー：{error_message}",
    "ko": "자막 파일 로드 오류: {error_message}",
    "hi": "उपशीर्षक फ़ाइल लोड करने में त्रुटि: {error_message}"
}
ERROR_CONVERT_TIMESTAMP = {
    "en": "Failed to convert timestamp '{timestamp}' for format '{format_type}'",
    "es": "Error al convertir la marca de tiempo '{timestamp}' para el formato '{format_type}'",
    "tr": "'{timestamp}' zaman damgası '{format_type}' formatına dönüştürülemedi",
    "zh": "无法将时间戳 '{timestamp}' 转换为格式 '{format_type}'",
    "ru": "Не удалось преобразовать метку времени '{timestamp}' в формат '{format_type}'",
    "pl": "Nie udało się przekonwertować znacznika czasu '{timestamp}' na format '{format_type}'",
    "uk": "Не вдалося перетворити мітку часу '{timestamp}' на формат '{format_type}'",
    "ja": "タイムスタンプ '{timestamp}' をフォーマット '{format_type}' に変換できませんでした",
    "ko": "타임스탬프 '{timestamp}'를 형식 '{format_type}'으로 변환하지 못했습니다",
    "hi": "टाइमस्टैम्प '{timestamp}' को प्रारूप '{format_type}' में परिवर्तित करने में विफल"
}
ERROR_PARSING_TIME_STRING = {
    "en": "Error parsing time string '{time_str}'",
    "es": "Error al analizar la cadena de tiempo '{time_str}'",
    "tr": "'{time_str}' zaman dizesi ayrıştırılırken hata",
    "zh": "解析时间字符串 '{time_str}' 时出错",
    "ru": "Ошибка разбора временной строки '{time_str}'",
    "pl": "Błąd podczas analizowania ciągu czasu '{time_str}'",
    "uk": "Помилка розбору рядка часу '{time_str}'",
    "ja": "時間文字列 '{time_str}' の解析エラー",
    "ko": "시간 문자열 '{time_str}' 구문 분석 오류",
    "hi": "समय स्ट्रिंग '{time_str}' को पार्स करने में त्रुटि"
}
ERROR_PARSING_TIME_STRING_DETAILED = {
    "en": "Error parsing time string '{time_str}' for format '{format_type}': {error_message}",
    "es": "Error al analizar la cadena de tiempo '{time_str}' para el formato '{format_type}': {error_message}",
    "tr": "'{time_str}' zaman dizesi '{format_type}' formatı için ayrıştırılırken hata: {error_message}",
    "zh": "解析时间字符串 '{time_str}' 为格式 '{format_type}' 时出错：{error_message}",
    "ru": "Ошибка разбора временной строки '{time_str}' для формата '{format_type}': {error_message}",
    "pl": "Błąd podczas analizowania ciągu czasu '{time_str}' dla formatu '{format_type}': {error_message}",
    "uk": "Помилка розбору рядка часу '{time_str}' для формату '{format_type}': {error_message}",
    "ja": "フォーマット '{format_type}' の時間文字列 '{time_str}' の解析エラー：{error_message}",
    "ko": "형식 '{format_type}'의 시간 문자열 '{time_str}' 구문 분석 오류: {error_message}",
    "hi": "प्रारूप '{format_type}' के लिए समय स्ट्रिंग '{time_str}' को पार्स करने में त्रुटि: {error_message}"
}
NO_FILES_TO_SYNC = {
    "en": "No files to sync. Please add files to the batch list.",
    "es": "No hay archivos para sincronizar. Por favor, agregue archivos a la lista de lotes.",
    "tr": "Senkronize edilecek dosya yok. Lütfen toplu listeye dosya ekleyin.",
    "zh": "没有要同步的文件。请将文件添加到批处理列表。",
    "ru": "Нет файлов для синхронизации. Пожалуйста, добавьте файлы в список пакетов.",
    "pl": "Brak plików do synchronizacji. Proszę dodać pliki do listy wsadowej.",
    "uk": "Немає файлів для синхронізації. Будь ласка, додайте файли до списку пакетів.",
    "ja": "同期するファイルがありません。バッチリストにファイルを追加してください。",
    "ko": "동기화할 파일이 없습니다. 배치 목록에 파일을 추가하세요.",
    "hi": "सिंक करने के लिए कोई फ़ाइल नहीं है। कृपया बैच सूची में फ़ाइलें जोड़ें।"
}
NO_VALID_FILE_PAIRS = {
    "en": "No valid file pairs to sync.",
    "es": "No hay pares de archivos válidos para sincronizar.",
    "tr": "Senkronize edilecek geçerli dosya çifti yok.",
    "zh": "没有有效的文件对要同步。",
    "ru": "Нет действительных пар файлов для синхронизации.",
    "pl": "Brak prawidłowych par plików do synchronizacji.",
    "uk": "Немає дійсних пар файлів для синхронізації.",
    "ja": "同期する有効なファイルペアがありません。",
    "ko": "동기화할 유효한 파일 쌍이 없습니다.",
    "hi": "सिंक करने के लिए कोई मान्य फ़ाइल जोड़ी नहीं है।"
}
ERROR_PROCESS_TERMINATION = {
    "en": "Error occurred during process termination: {error_message}",
    "es": "Ocurrió un error durante la terminación del proceso: {error_message}",
    "tr": "İşlem sonlandırma sırasında hata oluştu: {error_message}",
    "zh": "在进程终止期间发生错误：{error_message}",
    "ru": "Произошла ошибка во время завершения процесса: {error_message}",
    "pl": "Błąd podczas zakończenia procesu: {error_message}",
    "uk": "Помилка під час завершення процесу: {error_message}",
    "ja": "プロセス終了中にエラーが発生しました：{error_message}",
    "ko": "프로세스 종료 중 오류 발생: {error_message}",
    "hi": "प्रक्रिया समाप्ति के दौरान त्रुटि: {error_message}"
}
AUTO_SYNC_CANCELLED = {
    "en": "Automatic synchronization cancelled.",
    "es": "Sincronización automática cancelada.",
    "tr": "Otomatik senkronizasyon iptal edildi.",
    "zh": "自动同步已取消。",
    "ru": "Автоматическая синхронизация отменена.",
    "pl": "Automatyczna synchronizacja anulowana.",
    "uk": "Автоматична синхронізація скасована.",
    "ja": "自動同期がキャンセルされました。",
    "ko": "자동 동기화가 취소되었습니다.",
    "hi": "स्वचालित सिंक्रनाइज़ेशन रद्द कर दिया गया।"
}
BATCH_SYNC_CANCELLED = {
    "en": "Batch synchronization cancelled.",
    "es": "Sincronización por lotes cancelada.",
    "tr": "Toplu senkronizasyon iptal edildi.",
    "zh": "批量同步已取消。",
    "ru": "Пакетная синхронизация отменена.",
    "pl": "Synchronizacja wsadowa anulowana.",
    "uk": "Пакетна синхронізація скасована.",
    "ja": "バッチ同期がキャンセルされました。",
    "ko": "배치 동기화가 취소되었습니다.",
    "hi": "बैच सिंक्रनाइज़ेशन रद्द कर दिया गया।"
}
NO_SYNC_PROCESS = {
    "en": "No synchronization process to cancel.",
    "es": "No hay proceso de sincronización para cancelar.",
    "tr": "İptal edilecek senkronizasyon işlemi yok.",
    "zh": "没有要取消的同步进程。",
    "ru": "Нет процесса синхронизации для отмены.",
    "pl": "Brak procesu synchronizacji do anulowania.",
    "uk": "Немає процесу синхронізації для скасування.",
    "ja": "キャンセルする同期プロセスがありません。",
    "ko": "취소할 동기화 프로세스가 없습니다.",
    "hi": "रद्द करने के लिए कोई सिंक्रनाइज़ेशन प्रक्रिया नहीं है।"
}
INVALID_SYNC_TOOL = {
    "en": "Invalid sync tool selected.",
    "es": "Herramienta de sincronización inválida seleccionada.",
    "tr": "Geçersiz senkronizasyon aracı seçildi.",
    "zh": "选择了无效的同步工具。",
    "ru": "Выбран недопустимый инструмент синхронизации.",
    "pl": "Wybrano nieprawidłowe narzędzie synchronizacji.",
    "uk": "Вибрано недійсний інструмент синхронізації.",
    "ja": "無効な同期ツールが選択されました。",
    "ko": "잘못된 동기화 도구가 선택되었습니다.",
    "hi": "अमान्य सिंक टूल चुना गया।"
}
FAILED_START_PROCESS = {
    "en": "Failed to start process: {error_message}",
    "es": "Error al iniciar el proceso: {error_message}",
    "tr": "İşlem başlatılamadı: {error_message}",
    "zh": "无法启动进程：{error_message}",
    "ru": "Не удалось запустить процесс: {error_message}",
    "pl": "Nie udało się uruchomić procesu: {error_message}",
    "uk": "Не вдалося запустити процес: {error_message}",
    "ja": "プロセスの開始に失敗しました：{error_message}",
    "ko": "프로세스를 시작하지 못했습니다: {error_message}",
    "hi": "प्रक्रिया प्रारंभ करने में विफल: {error_message}"
}
ERROR_OCCURRED = {
    "en": "Error occurred: {error_message}",
    "es": "Ocurrió un error: {error_message}",
    "tr": "Hata oluştu: {error_message}",
    "zh": "发生错误：{error_message}",
    "ru": "Произошла ошибка: {error_message}",
    "pl": "Wystąpił błąd: {error_message}",
    "uk": "Виникла помилка: {error_message}",
    "ja": "エラーが発生しました：{error_message}",
    "ko": "오류 발생: {error_message}",
    "hi": "त्रुटि हुई: {error_message}"
}
ERROR_EXECUTING_COMMAND = {
    "en": "Error executing command: ",
    "es": "Error al ejecutar el comando: ",
    "tr": "Komut yürütülürken hata: ",
    "zh": "执行命令时出错：",
    "ru": "Ошибка выполнения команды: ",
    "pl": "Błąd podczas wykonywania polecenia: ",
    "uk": "Помилка виконання команди: ",
    "ja": "コマンドの実行エラー：",
    "ko": "명령 실행 오류: ",
    "hi": "कमांड निष्पादित करने में त्रुटि: "
}
DROP_VALID_FILES = {
    "en": "Please drop valid subtitle and video files.",
    "es": "Por favor, suelte archivos de subtítulos y video válidos.",
    "tr": "Lütfen geçerli altyazı ve video dosyalarını bırakın.",
    "zh": "请拖放有效的字幕和视频文件。",
    "ru": "Пожалуйста, перетащите действительные файлы субтитров и видео.",
    "pl": "Proszę upuścić prawidłowe pliki napisów i wideo.",
    "uk": "Будь ласка, перетягніть дійсні файли субтитрів та відео.",
    "ja": "有効な字幕ファイルと動画ファイルをドロップしてください。",
    "ko": "유효한 자막 및 비디오 파일을 드롭하세요.",
    "hi": "कृपया मान्य उपशीर्षक और वीडियो फ़ाइलें छोड़ें।"
}
PAIRS_ADDED = {
    "en": "Added {count} pair(s)",
    "es": "Agregado {count} par(es)",
    "tr": "{count} çift eklendi",
    "zh": "添加了 {count} 对",
    "ru": "Добавлено {count} пар(ы)",
    "pl": "Dodano {count} par(y)",
    "uk": "Додано {count} пар(и)",
    "ja": "{count} ペア追加されました",
    "ko": "{count} 쌍이 추가되었습니다",
    "hi": "{count} जोड़ी जोड़ी गई"
}
UNPAIRED_FILES_ADDED = {
    "en": "Added {count} unpaired file(s)",
    "es": "Agregado {count} archivo(s) no emparejado(s)",
    "tr": "{count} eşleşmemiş dosya eklendi",
    "zh": "添加了 {count} 个未配对文件",
    "ru": "Добавлено {count} несопоставленный файл(ы)",
    "pl": "Dodano {count} niesparowanych plików",
    "uk": "Додано {count} непоєднаних файлів",
    "ja": "{count} 個の未ペアファイルが追加されました",
    "ko": "{count}개의 페어링되지 않은 파일이 추가되었습니다",
    "hi": "{count} अजुड़ी फ़ाइलें जोड़ी गईं"
}
UNPAIRED_FILES = {
    "en": "{count} unpaired file(s)",
    "es": "{count} archivo(s) no emparejado(s)",
    "tr": "{count} eşleşmemiş dosya var",
    "zh": "{count} 个未配对文件",
    "ru": "{count} несопоставленный файл(ы)",
    "pl": "{count} niesparowany plik(i)",
    "uk": "{count} непоєднаний(і) файл(и)",
    "ja": "{count} 個の未ペアファイル",
    "ko": "{count}개의 페어링되지 않은 파일",
    "hi": "{count} अजुड़ी फ़ाइलें"
}
DUPLICATE_PAIRS_SKIPPED = {
    "en": "{count} duplicate pair(s) skipped",
    "es": "{count} par(es) duplicado(s) omitido(s)",
    "tr": "{count} yinelenen çift atlandı",
    "zh": "跳过 {count} 个重复对",
    "ru": "{count} дублированный пар(а) пропущен(о)",
    "pl": "Pominięto {count} zduplikowaną(e) parę(y)",
    "uk": "Пропущено {count} дубльовану(і) пару(и)",
    "ja": "{count} 重複ペアがスキップされました",
    "ko": "{count}개의 중복 쌍이 건너뛰어졌습니다",
    "hi": "{count} डुप्लिकेट जोड़ी(याँ) छोड़ी गईं"
}
PAIR_ADDED = {
    "en": "Added 1 pair.",
    "es": "Agregado 1 par.",
    "tr": "1 çift eklendi.",
    "zh": "添加了 1 对。",
    "ru": "Добавлена 1 пара.",
    "pl": "Dodano 1 parę.",
    "uk": "Додано 1 пару.",
    "ja": "1 ペア追加されました。",
    "ko": "1 쌍이 추가되었습니다.",
    "hi": "1 जोड़ी जोड़ी गई।"
}
SAME_FILE_ERROR = {
    "en": "Cannot use the same file for both inputs.",
    "es": "No se puede usar el mismo archivo para ambas entradas.",
    "tr": "Her iki giriş için de aynı dosya kullanılamaz.",
    "zh": "无法同时使用同一文件作为两个输入。",
    "ru": "Нельзя использовать один и тот же файл для обоих входов.",
    "pl": "Nie można użyć tego samego pliku dla obu wejść.",
    "uk": "Не можна використовувати один і той самий файл для обох входів.",
    "ja": "両方の入力に同じファイルを使用することはできません。",
    "ko": "두 입력 모두에 동일한 파일을 사용할 수 없습니다.",
    "hi": "दोनों इनपुट के लिए एक ही फ़ाइल का उपयोग नहीं किया जा सकता।"
}
PAIR_ALREADY_EXISTS = {
    "en": "This pair already exists. Please select a different file.",
    "es": "Este par ya existe. Por favor, seleccione un archivo diferente.",
    "tr": "Bu çift zaten mevcut. Lütfen farklı bir dosya seçin.",
    "zh": "此对已存在。请选择其他文件。",
    "ru": "Эта пара уже существует. Пожалуйста, выберите другой файл.",
    "pl": "Ta para już istnieje. Proszę wybrać inny plik.",
    "uk": "Ця пара вже існує. Будь ласка, виберіть інший файл.",
    "ja": "このペアは既に存在します。別のファイルを選択してください。",
    "ko": "이 쌍은 이미 존재합니다. 다른 파일을 선택하세요.",
    "hi": "यह जोड़ी पहले से मौजूद है। कृपया एक अलग फ़ाइल चुनें।"
}
SUBTITLE_ADDED = {
    "en": "Subtitle added.",
    "es": "Subtítulo agregado.",
    "tr": "Altyazı eklendi.",
    "zh": "字幕已添加。",
    "ru": "Субтитры добавлены.",
    "pl": "Napisy dodane.",
    "uk": "Субтитри додано.",
    "ja": "字幕が追加されました。",
    "ko": "자막이 추가되었습니다.",
    "hi": "उपशीर्षक जोड़ा गया।"
}
VIDEO_ADDED = {
    "en": "Video/reference subtitle added.",
    "es": "Video/subtítulo de referencia agregado.",
    "tr": "Video/referans altyazı eklendi.",
    "zh": "视频/参考字幕已添加。",
    "ru": "Видео/справочный субтитр добавлен.",
    "pl": "Dodano wideo/napisy referencyjne.",
    "uk": "Додано відео/довідкові субтитри.",
    "ja": "動画/参照字幕が追加されました。",
    "ko": "비디오/참조 자막이 추가되었습니다.",
    "hi": "वीडियो/संदर्भ उपशीर्षक जोड़ा गया।"
}
FILE_CHANGED = {
    "en": "File changed.",
    "es": "Archivo cambiado.",
    "tr": "Dosya değiştirildi.",
    "zh": "文件已更改。",
    "ru": "Файл изменен.",
    "pl": "Plik zmieniony.",
    "uk": "Файл змінено.",
    "ja": "ファイルが変更されました。",
    "ko": "파일이 변경되었습니다.",
    "hi": "फ़ाइल बदली गई।"
}
SELECT_ITEM_TO_CHANGE = {
    "en": "Please select an item to change.",
    "es": "Por favor, seleccione un elemento para cambiar.",
    "tr": "Lütfen değiştirmek için bir öğe seçin.",
    "zh": "请选择要更改的项目。",
    "ru": "Пожалуйста, выберите элемент для изменения.",
    "pl": "Proszę wybrać element do zmiany.",
    "uk": "Будь ласка, виберіть елемент для зміни.",
    "ja": "変更する項目を選択してください。",
    "ko": "변경할 항목을 선택하세요.",
    "hi": "कृपया बदलने के लिए एक आइटम चुनें।"
}
SELECT_ITEM_TO_REMOVE = {
    "en": "Please select an item to remove.",
    "es": "Por favor, seleccione un elemento para eliminar.",
    "tr": "Lütfen kaldırmak için bir öğe seçin.",
    "zh": "请选择要删除的项目。",
    "ru": "Пожалуйста, выберите элемент для удаления.",
    "pl": "Proszę wybrać element do usunięcia.",
    "uk": "Будь ласка, виберіть елемент для видалення.",
    "ja": "削除する項目を選択してください。",
    "ko": "제거할 항목을 선택하세요.",
    "hi": "कृपया हटाने के लिए एक आइटम चुनें।"
}
FILE_NOT_EXIST = {
    "en": "File specified in the argument does not exist.",
    "es": "El archivo especificado en el argumento no existe.",
    "tr": "Argümanda belirtilen dosya mevcut değil.",
    "zh": "参数中指定的文件不存在。",
    "ru": "Файл, указанный в аргументе, не существует.",
    "pl": "Plik określony w argumencie nie istnieje.",
    "uk": "Файл, вказаний в аргументі, не існує.",
    "ja": "引数で指定されたファイルが存在しません。",
    "ko": "인수에 지정된 파일이 존재하지 않습니다.",
    "hi": "तर्क में निर्दिष्ट फ़ाइल मौजूद नहीं है।"
}
MULTIPLE_ARGUMENTS = {
    "en": "Multiple arguments provided. Please provide only one subtitle file path.",
    "es": "Se proporcionaron múltiples argumentos. Por favor, proporcione solo una ruta de archivo de subtítulos.",
    "tr": "Birden fazla argüman sağlandı. Lütfen yalnızca bir altyazı dosyası yolu sağlayın.",
    "zh": "提供了多个参数。请只提供一个字幕文件路径。",
    "ru": "Предоставлено несколько аргументов. Пожалуйста, укажите только один путь к файлу субтитров.",
    "pl": "Podano wiele argumentów. Proszę podać tylko jedną ścieżkę do pliku napisów.",
    "uk": "Надано кілька аргументів. Будь ласка, вкажіть лише один шлях до файлу субтитрів.",
    "ja": "複数の引数が提供されました。字幕ファイルのパスを1つだけ指定してください。",
    "ko": "여러 인수가 제공되었습니다. 자막 파일 경로를 하나만 제공하세요.",
    "hi": "कई तर्क प्रदान किए गए हैं। कृपया केवल एक उपशीर्षक फ़ाइल पथ प्रदान करें।"
}
INVALID_FILE_FORMAT = {
    "en": "Invalid file format. Please provide a subtitle file.",
    "es": "Formato de archivo inválido. Por favor, proporcione un archivo de subtítulos.",
    "tr": "Geçersiz dosya formatı. Lütfen bir altyazı dosyası sağlayın.",
    "zh": "无效的文件格式。请提供一个字幕文件。",
    "ru": "Недопустимый формат файла. Пожалуйста, укажите файл субтитров.",
    "pl": "Nieprawidłowy format pliku. Proszę podać plik napisów.",
    "uk": "Недійсний формат файлу. Будь ласка, вкажіть файл субтитрів.",
    "ja": "無効なファイル形式です。字幕ファイルを指定してください。",
    "ko": "잘못된 파일 형식입니다. 자막 파일을 제공하세요.",
    "hi": "अमान्य फ़ाइल प्रारूप। कृपया एक उपशीर्षक फ़ाइल प्रदान करें।"
}
INVALID_SYNC_TOOL_SELECTED = {
    "en": "Invalid sync tool selected.",
    "es": "Herramienta de sincronización inválida seleccionada.",
    "tr": "Geçersiz senkronizasyon aracı seçildi.",
    "zh": "选择了无效的同步工具。",
    "ru": "Выбран недопустимый инструмент синхронизации.",
    "pl": "Wybrano nieprawidłowe narzędzie synchronizacji.",
    "uk": "Вибрано недійсний інструмент синхронізації.",
    "ja": "無効な同期ツールが選択されました。",
    "ko": "잘못된 동기화 도구가 선택되었습니다.",
    "hi": "अमान्य सिंक टूल चुना गया।"
}
TEXT_SELECTED_FOLDER = {
    "en": "Selected folder: {}",
    "es": "Carpeta seleccionada: {}",
    "tr": "Seçilen klasör: {}",
    "zh": "已选择文件夹：{}",
    "ru": "Выбранная папка: {}",
    "pl": "Wybrany folder: {}",
    "uk": "Вибрана папка: {}",
    "ja": "選択されたフォルダ：{}",
    "ko": "선택된 폴더: {}",
    "hi": "चयनित फ़ोल्डर: {}"
}
TEXT_NO_FOLDER_SELECTED = {
    "en": "No folder selected.",
    "es": "No se seleccionó ninguna carpeta.",
    "tr": "Klasör seçilmedi.",
    "zh": "未选择文件夹。",
    "ru": "Папка не выбрана.",
    "pl": "Nie wybrano folderu.",
    "uk": "Папку не вибрано.",
    "ja": "フォルダが選択されていません。",
    "ko": "폴더가 선택되지 않았습니다.",
    "hi": "कोई फ़ोल्डर चयनित नहीं है।"
}
TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST = {
    "en": "The selected destination folder does not exist.",
    "es": "La carpeta de destino seleccionada no existe.",
    "tr": "Seçilen hedef klasör mevcut değil.",
    "zh": "所选的目标文件夹不存在。",
    "ru": "Выбранная папка назначения не существует.",
    "pl": "Wybrany folder docelowy nie istnieje.",
    "uk": "Вибрана папка призначення не існує.",
    "ja": "選択した宛先フォルダが存在しません。",
    "ko": "선택한 대상 폴더가 존재하지 않습니다.",
    "hi": "चयनित गंतव्य फ़ोल्डर मौजूद नहीं है।"
}
ADDED_PAIRS_MSG = {
    "en": "{} pairs automatically matched",
    "es": "{} pares emparejados automáticamente",
    "tr": "{} çift otomatik olarak eşleştirildi",
    "zh": "{} 对字幕自动匹配",
    "ru": "{} пары автоматически сопоставлены",
    "pl": "{} par automatycznie dopasowanych",
    "uk": "{} пар автоматично зіставлено",
    "ja": "{} ペアが自動的に一致しました",
    "ko": "{} 쌍이 자동으로 일치되었습니다",
    "hi": "{} जोड़ी स्वचालित रूप से मिलाई गई"
}
SKIPPED_DUPLICATES_MSG = {
    "en": "Skipped {} duplicate pair{}",
    "es": "Omitido {} par{} duplicado{}",
    "tr": "{} yinelenen çift atlandı",
    "zh": "跳过 {} 个重复对",
    "ru": "Пропущено {} дублированный пар{а}",
    "pl": "Pominięto {} zduplikowaną(e) parę(y)",
    "uk": "Пропущено {} дубльовану(і) пару(и)",
    "ja": "{} 重複ペアがスキップされました",
    "ko": "{}개의 중복 쌍이 건너뛰어졌습니다",
    "hi": "{} डुप्लिकेट जोड़ी(याँ) छोड़ी गईं"
}
INVALID_PARENT_ITEM = {
    "en": "Invalid parent item with no values.",
    "es": "Elemento principal inválido sin valores.",
    "tr": "Değer içermeyen geçersiz üst öğe.",
    "zh": "无值的无效父项目。",
    "ru": "Недопустимый родительский элемент без значений.",
    "pl": "Nieprawidłowy element nadrzędny bez wartości.",
    "uk": "Недійсний батьківський елемент без значень.",
    "ja": "値のない無効な親アイテム。",
    "ko": "값이 없는 잘못된 상위 항목.",
    "hi": "कोई मान नहीं वाला अमान्य पैरेंट आइटम।"
}
SKIP_NO_VIDEO_NO_SUBTITLE = {
    "en": "Skipping entry with no video and no subtitle.",
    "es": "Omitiendo entrada sin video ni subtítulo.",
    "tr": "Video ve altyazı olmayan girdi atlanıyor.",
    "zh": "跳过没有视频和没有字幕的条目。",
    "ru": "Пропуск записи без видео и субтитров.",
    "pl": "Pomijanie wpisu bez wideo i napisów.",
    "uk": "Пропуск запису без відео та субтитрів.",
    "ja": "ビデオと字幕のないエントリをスキップしています。",
    "ko": "비디오와 자막이 없는 항목 건너뛰기.",
    "hi": "कोई वीडियो और कोई उपशीर्षक नहीं वाली प्रविष्टि छोड़ना।"
}
SKIP_NO_SUBTITLE = {
    "en": "Skipping '{video_file}': No subtitle file.",
    "es": "Omitiendo '{video_file}': No hay archivo de subtítulos.",
    "tr": "'{video_file}' atlanıyor: Altyazı dosyası yok.",
    "zh": "跳过 '{video_file}'：没有字幕文件。",
    "ru": "Пропуск '{video_file}': Нет файла субтитров.",
    "pl": "Pomijanie '{video_file}': Brak pliku napisów.",
    "uk": "Пропуск '{video_file}': Немає файлу субтитрів.",
    "ja": "'{video_file}' をスキップしています：字幕ファイルがありません。",
    "ko": "'{video_file}' 건너뛰기: 자막 파일이 없습니다.",
    "hi": "'{video_file}' छोड़ना: कोई उपशीर्षक फ़ाइल नहीं।"
}
SKIP_NO_VIDEO = {
    "en": "Skipping '{subtitle_file}': No video/reference file.",
    "es": "Omitiendo '{subtitle_file}': No hay archivo de video/referencia.",
    "tr": "'{subtitle_file}' atlanıyor: Video/referans dosyası yok.",
    "zh": "跳过 '{subtitle_file}'：没有视频/参考文件。",
    "ru": "Пропуск '{subtitle_file}': Нет видео/справочного файла.",
    "pl": "Pomijanie '{subtitle_file}': Brak pliku wideo/referencyjnego.",
    "uk": "Пропуск '{subtitle_file}': Немає відео/довідкового файлу.",
    "ja": "'{subtitle_file}' をスキップしています：ビデオ/参照ファイルがありません。",
    "ko": "'{subtitle_file}' 건너뛰기: 비디오/참조 파일이 없습니다.",
    "hi": "'{subtitle_file}' छोड़ना: कोई वीडियो/संदर्भ फ़ाइल नहीं।"
}
SKIP_UNPAIRED_ITEM = {
    "en": "Unpaired item skipped.",
    "es": "Elemento no emparejado omitido.",
    "tr": "Eşleşmemiş öğe atlandı.",
    "zh": "跳过未配对的项目。",
    "ru": "Пропущен несопоставленный элемент.",
    "pl": "Pominięto niesparowany element.",
    "uk": "Пропущено непоєднаний елемент.",
    "ja": "未ペアのアイテムをスキップしました。",
    "ko": "페어링되지 않은 항목 건너뛰기.",
    "hi": "अजुड़ा आइटम छोड़ा गया।"
}
SKIPPING_ALREADY_SYNCED = {
    "en": "Skipping {filename}: Already synced.",
    "es": "Omitiendo {filename}: Ya sincronizado.",
    "tr": "{filename} atlanıyor: Zaten senkronize.",
    "zh": "跳过 {filename}：已同步。",
    "ru": "Пропуск {filename}: Уже синхронизирован.",
    "pl": "Pomijanie {filename}: Już zsynchronizowane.",
    "uk": "Пропуск {filename}: Вже синхронізовано.",
    "ja": "{filename} をスキップしています：既に同期されています。",
    "ko": "{filename} 건너뛰기: 이미 동기화됨.",
    "hi": "{filename} छोड़ना: पहले से सिंक किया गया।"
}
CONVERTING_SUBTITLE = {
    "en": "Converting {file_extension} to SRT...",
    "es": "Convirtiendo {file_extension} a SRT...",
    "tr": "{file_extension} uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 {file_extension} 转换为 SRT...",
    "ru": "Преобразование {file_extension} в SRT...",
    "pl": "Konwertowanie {file_extension} na SRT...",
    "uk": "Перетворення {file_extension} на SRT...",
    "ja": "{file_extension} を SRT に変換しています...",
    "ko": "{file_extension}를 SRT로 변환 중...",
    "hi": "{file_extension} को SRT में परिवर्तित किया जा रहा है..."
}
SYNCING_LOG_TEXT = {
    "en": "[{}/{}] Syncing {} with {}...\n",
    "es": "[{}/{}] Sincronizando {} con {}...\n",
    "tr": "[{}/{}] {} ile {} senkronize ediliyor...\n",
    "zh": "[{}/{}] 正在同步 {} 和 {}...\n",
    "ru": "[{}/{}] Синхронизация {} с {}...\n",
    "pl": "[{}/{}] Synchronizowanie {} z {}...\n",
    "uk": "[{}/{}] Синхронізація {} з {}...\n",
    "ja": "[{}/{}] {} と {} を同期しています...\n",
    "ko": "[{}/{}] {}와 {} 동기화 중...\n",
    "hi": "[{}/{}] {} को {} के साथ सिंक कर रहा है...\n"
}
ERROR_CONVERTING_SUBTITLE = {
    "en": "Error converting subtitle: {error_message}",
    "es": "Error al convertir subtítulo: {error_message}",
    "tr": "Altyazı dönüştürme hatası: {error_message}",
    "zh": "转换字幕时出错：{error_message}",
    "ru": "Ошибка преобразования субтитров: {error_message}",
    "pl": "Błąd konwersji napisów: {error_message}",
    "uk": "Помилка перетворення субтитрів: {error_message}",
    "ja": "字幕の変換エラー：{error_message}",
    "ko": "자막 변환 오류: {error_message}",
    "hi": "उपशीर्षक परिवर्तित करने में त्रुटि: {error_message}"
}
SUBTITLE_CONVERTED = {
    "en": "Subtitle successfully converted and saved to: {srt_file}.",
    "es": "Subtítulo convertido exitosamente y guardado en: {srt_file}.",
    "tr": "Altyazı başarıyla dönüştürüldü ve kaydedildi: {srt_file}.",
    "zh": "字幕成功转换并保存到：{srt_file}。",
    "ru": "Субтитры успешно преобразованы и сохранены в: {srt_file}.",
    "pl": "Napisy pomyślnie przekonwertowane i zapisane do: {srt_file}.",
    "uk": "Субтитри успішно перетворено та збережено до: {srt_file}.",
    "ja": "字幕が正常に変換され、保存先：{srt_file}。",
    "ko": "자막이 성공적으로 변환되어 저장됨: {srt_file}.",
    "hi": "उपशीर्षक सफलतापूर्वक परिवर्तित और यहाँ सहेजा गया: {srt_file}।"
}
ERROR_UNSUPPORTED_CONVERSION = {
    "en": "Error: Conversion for {file_extension} is not supported.",
    "es": "Error: La conversión para {file_extension} no está soportada.",
    "tr": "Hata: {file_extension} dönüştürme desteklenmiyor.",
    "zh": "错误：不支持 {file_extension} 的转换。",
    "ru": "Ошибка: Конвертация для {file_extension} не поддерживается.",
    "pl": "Błąd: Konwersja dla {file_extension} nie jest obsługiwana.",
    "uk": "Помилка: Перетворення для {file_extension} не підтримується.",
    "ja": "エラー：{file_extension} の変換はサポートされていません。",
    "ko": "오류: {file_extension} 변환이 지원되지 않습니다.",
    "hi": "त्रुटि: {file_extension} के लिए रूपांतरण समर्थित नहीं है।"
}
FAILED_CONVERT_SUBTITLE = {
    "en": "Failed to convert subtitle file: {subtitle_file}",
    "es": "Error al convertir el archivo de subtítulos: {subtitle_file}",
    "tr": "Altyazı dosyası dönüştürülemedi: {subtitle_file}",
    "zh": "无法转换字幕文件：{subtitle_file}",
    "ru": "Не удалось преобразовать файл субтитров: {subtitle_file}",
    "pl": "Nie udało się przekonwertować pliku napisów: {subtitle_file}",
    "uk": "Не вдалося перетворити файл субтитрів: {subtitle_file}",
    "ja": "字幕ファイルの変換に失敗しました：{subtitle_file}",
    "ko": "자막 파일을 변환하지 못했습니다: {subtitle_file}",
    "hi": "उपशीर्षक फ़ाइल परिवर्तित करने में विफल: {subtitle_file}"
}
FAILED_CONVERT_VIDEO = {
    "en": "Failed to convert video/reference file: {video_file}",
    "es": "Error al convertir archivo de video/referencia: {video_file}",
    "tr": "Video/referans dosyası dönüştürülemedi: {video_file}",
    "zh": "无法转换视频/参考文件：{video_file}",
    "ru": "Не удалось преобразовать видео/справочный файл: {video_file}",
    "pl": "Nie udało się przekonwertować pliku wideo/referencyjnego: {video_file}",
    "uk": "Не вдалося перетворити відео/довідковий файл: {video_file}",
    "ja": "ビデオ/参照ファイルの変換に失敗しました：{video_file}",
    "ko": "비디오/참조 파일을 변환하지 못했습니다: {video_file}",
    "hi": "वीडियो/संदर्भ फ़ाइल परिवर्तित करने में विफल: {video_file}"
}
SPLIT_PENALTY_ZERO = {
    "en": "Split penalty is set to 0. Using --no-split argument...",
    "es": "La penalización de división se establece en 0. Usando el argumento --no-split...",
    "tr": "Bölme cezası 0 olarak ayarlandı. --no-split argümanı kullanılıyor...",
    "zh": "分割惩罚设置为 0。使用 --no-split 参数...",
    "ru": "Штраф за разделение установлен на 0. Используется аргумент --no-split...",
    "pl": "Kara za podział jest ustawiona na 0. Używanie argumentu --no-split...",
    "uk": "Штраф за розділення встановлено на 0. Використання аргументу --no-split...",
    "ja": "分割ペナルティが0に設定されています。--no-split 引数を使用しています...",
    "ko": "분할 페널티가 0으로 설정되었습니다. --no-split 인수 사용 중...",
    "hi": "विभाजन पेनल्टी 0 पर सेट है। --no-split तर्क का उपयोग कर रहा है..."
}
SPLIT_PENALTY_SET = {
    "en": "Split penalty is set to {split_penalty}...",
    "es": "La penalización de división se establece en {split_penalty}...",
    "tr": "Bölme cezası {split_penalty} olarak ayarlandı...",
    "zh": "分割惩罚设置为 {split_penalty}...",
    "ru": "Штраф за разделение установлен на {split_penalty}...",
    "pl": "Kara za podział jest ustawiona na {split_penalty}...",
    "uk": "Штраф за розділення встановлено на {split_penalty}...",
    "ja": "分割ペナルティが {split_penalty} に設定されています...",
    "ko": "분할 페널티가 {split_penalty}으로 설정되었습니다...",
    "hi": "विभाजन पेनल्टी {split_penalty} पर सेट है..."
}
USING_REFERENCE_SUBTITLE = {
    "en": "Using reference subtitle for syncing...",
    "es": "Usando subtítulo de referencia para sincronizar...",
    "tr": "Senkronizasyon için referans altyazı kullanılıyor...",
    "zh": "使用参考字幕进行同步...",
    "ru": "Использование справочных субтитров для синхронизации...",
    "pl": "Używanie napisów referencyjnych do synchronizacji...",
    "uk": "Використання довідкових субтитрів для синхронізації...",
    "ja": "同期に参照字幕を使用しています...",
    "ko": "동기화에 참조 자막 사용 중...",
    "hi": "सिंकिंग के लिए संदर्भ उपशीर्षक का उपयोग कर रहा है..."
}
USING_VIDEO_FOR_SYNC = {
    "en": "Using video for syncing...",
    "es": "Usando video para sincronizar...",
    "tr": "Senkronizasyon için video kullanılıyor...",
    "zh": "使用视频进行同步...",
    "ru": "Использование видео для синхронизации...",
    "pl": "Używanie wideo do synchronizacji...",
    "uk": "Використання відео для синхронізації...",
    "ja": "同期にビデオを使用しています...",
    "ko": "동기화에 비디오 사용 중...",
    "hi": "सिंकिंग के लिए वीडियो का उपयोग कर रहा है..."
}
ENABLED_NO_FIX_FRAMERATE = {
    "en": "Enabled: Don't fix framerate.",
    "es": "Habilitado: No corregir la velocidad de fotogramas.",
    "tr": "Etkinleştirildi: Kare hızını düzeltme.",
    "zh": "已启用：不修复帧速率。",
    "ru": "Включено: Не исправлять частоту кадров.",
    "pl": "Włączono: Nie naprawiaj częstotliwości klatek.",
    "uk": "Увімкнено: Не виправляти частоту кадрів.",
    "ja": "有効化：フレームレートを修正しない。",
    "ko": "활성화됨: 프레임 속도 수정 안 함.",
    "hi": "सक्षम: फ्रेम दर को ठीक न करें।"
}
ENABLED_GSS = {
    "en": "Enabled: Golden-section search.",
    "es": "Habilitado: Búsqueda de sección áurea.",
    "tr": "Etkinleştirildi: Altın oran araması.",
    "zh": "已启用：黄金分割搜索。",
    "ru": "Включено: Поиск золотого сечения.",
    "pl": "Włączono: Wyszukiwanie złotego podziału.",
    "uk": "Увімкнено: Пошук золотого перетину.",
    "ja": "有効化：黄金分割探索。",
    "ko": "활성화됨: 황금 분할 검색.",
    "hi": "सक्षम: स्वर्ण-खंड खोज।"
}
ENABLED_AUDITOK_VAD = {
    "en": "Enabled: Using auditok instead of WebRTC's VAD.",
    "es": "Habilitado: Usando auditok en lugar de VAD de WebRTC.",
    "tr": "Etkinleştirildi: WebRTC'nin VAD'si yerine auditok kullanılıyor.",
    "zh": "已启用：使用 auditok 而不是 WebRTC 的 VAD。",
    "ru": "Включено: Использование auditok вместо VAD WebRTC.",
    "pl": "Włączono: Używanie auditok zamiast VAD WebRTC.",
    "uk": "Увімкнено: Використання auditok замість VAD WebRTC.",
    "ja": "有効化：WebRTCのVADの代わりにauditokを使用。",
    "ko": "활성화됨: WebRTC의 VAD 대신 auditok 사용.",
    "hi": "सक्षम: WebRTC के VAD के बजाय auditok का उपयोग।"
}
ADDITIONAL_ARGS_ADDED = {
    "en": "Additional arguments: {additional_args}",
    "es": "Argumentos adicionales: {additional_args}",
    "tr": "Ek argümanlar: {additional_args}",
    "zh": "附加参数：{additional_args}",
    "ru": "Дополнительные аргументы: {additional_args}",
    "pl": "Dodatkowe argumenty: {additional_args}",
    "uk": "Додаткові аргументи: {additional_args}",
    "ja": "追加引数：{additional_args}",
    "ko": "추가 인수: {additional_args}",
    "hi": "अतिरिक्त तर्क: {additional_args}"
}
SYNCING_STARTED = {
    "en": "Syncing started:",
    "es": "Sincronización iniciada:",
    "tr": "Senkronizasyon başlatıldı:",
    "zh": "开始同步：",
    "ru": "Синхронизация начата:",
    "pl": "Rozpoczęto synchronizację:",
    "uk": "Синхронізація розпочата:",
    "ja": "同期開始：",
    "ko": "동기화 시작:",
    "hi": "सिंकिंग शुरू:"
}
SYNCING_ENDED = {
    "en": "Syncing ended.",
    "es": "Sincronización finalizada.",
    "tr": "Senkronizasyon tamamlandı.",
    "zh": "同步结束。",
    "ru": "Синхронизация завершена.",
    "pl": "Synchronizacja zakończona.",
    "uk": "Синхронізація завершена.",
    "ja": "同期終了。",
    "ko": "동기화 종료.",
    "hi": "सिंकिंग समाप्त।"
}
SYNC_SUCCESS = {
    "en": "Success! Synchronized subtitle saved to: {output_subtitle_file}\n\n",
    "es": "¡Éxito! Subtítulo sincronizado guardado en: {output_subtitle_file}\n\n",
    "tr": "Başarılı! Senkronize altyazı kaydedildi: {output_subtitle_file}\n\n",
    "zh": "成功！同步字幕保存到：{output_subtitle_file}\n\n,",
    "ru": "Успех! Синхронизированные субтитры сохранены в: {output_subtitle_file}\n\n",
    "pl": "Sukces! Zsynchronizowane napisy zapisane do: {output_subtitle_file}\n\n",
    "uk": "Успіх! Синхронізовані субтитри збережено до: {output_subtitle_file}\n\n",
    "ja": "成功！同期した字幕の保存先：{output_subtitle_file}\n\n",
    "ko": "성공! 동기화된 자막 저장됨: {output_subtitle_file}\n\n",
    "hi": "सफल! सिंक्रनाइज़ किया गया उपशीर्षक यहाँ सहेजा गया: {output_subtitle_file}\n\n"
}
SYNC_ERROR = {
    "en": "Error occurred during synchronization of {filename}",
    "es": "Ocurrió un error durante la sincronización de {filename}",
    "tr": "{filename} senkronizasyonu sırasında hata oluştu",
    "zh": "同步 {filename} 时出错",
    "ru": "Произошла ошибка во время синхронизации {filename}",
    "pl": "Błąd podczas synchronizacji {filename}",
    "uk": "Помилка під час синхронізації {filename}",
    "ja": "{filename} の同期中にエラーが発生しました",
    "ko": "{filename} 동기화 중 오류 발생",
    "hi": "{filename} की सिंक्रनाइज़ेशन के दौरान त्रुटि हुई"
}
SYNC_ERROR_OCCURRED = {
    "en": "Error occurred during synchronization. Please check the log messages.",
    "es": "Ocurrió un error durante la sincronización. Por favor, revise los mensajes de registro.",
    "tr": "Senkronizasyon sırasında hata oluştu. Lütfen kayıt mesajlarını kontrol edin.",
    "zh": "同步期间发生错误。请检查日志消息。",
    "ru": "Произошла ошибка во время синхронизации. Пожалуйста, проверьте сообщения журнала.",
    "pl": "Wystąpił błąd podczas synchronizacji. Proszę sprawdzić komunikaty dziennika.",
    "uk": "Під час синхронізації сталася помилка. Будь ласка, перевірте повідомлення журналу.",
    "ja": "同期中にエラーが発生しました。ログメッセージを確認してください。",
    "ko": "동기화 중 오류가 발생했습니다. 로그 메시지를 확인하세요.",
    "hi": "सिंक्रनाइज़ेशन के दौरान त्रुटि हुई। कृपया लॉग संदेशों की जाँच करें।"
}
BATCH_SYNC_COMPLETED = {
    "en": "Batch syncing completed.",
    "es": "Sincronización por lotes completada.",
    "tr": "Toplu senkronizasyon tamamlandı.",
    "zh": "批量同步已完成。",
    "ru": "Пакетная синхронизация завершена.",
    "pl": "Zakończono synchronizację wsadową.",
    "uk": "Пакетну синхронізацію завершено.",
    "ja": "バッチ同期が完了しました。",
    "ko": "배치 동기화 완료.",
    "hi": "बैच सिंक्रनाइज़ेशन पूरा हुआ।"
}
PREPARING_SYNC = {
    "en": "Preparing {base_name}{file_extension} for automatic sync...",
    "es": "Preparando {base_name}{file_extension} para sincronización automática...",
    "tr": "Otomatik senkronizasyon için {base_name}{file_extension} hazırlanıyor...",
    "zh": "准备 {base_name}{file_extension} 进行自动同步...",
    "ru": "Подготовка {base_name}{file_extension} для автоматической синхронизации...",
    "pl": "Przygotowywanie {base_name}{file_extension} do automatycznej synchronizacji...",
    "uk": "Підготовка {base_name}{file_extension} до автоматичної синхронізації...",
    "ja": "自動同期のために {base_name}{file_extension} を準備しています...",
    "ko": "자동 동기화를 위해 {base_name}{file_extension} 준비 중...",
    "hi": "स्वचालित सिंक्रनाइज़ेशन के लिए {base_name}{file_extension} तैयार कर रहा है..."
}
CONVERTING_TTML = {
    "en": "Converting TTML/DFXP/ITT to SRT...",
    "es": "Convirtiendo TTML/DFXP/ITT a SRT...",
    "tr": "TTML/DFXP/ITT uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 TTML/DFXP/ITT 转换为 SRT...",
    "ru": "Преобразование TTML/DFXP/ITT в SRT...",
    "pl": "Konwertowanie TTML/DFXP/ITT na SRT...",
    "uk": "Перетворення TTML/DFXP/ITT на SRT...",
    "ja": "TTML/DFXP/ITT を SRT に変換しています...",
    "ko": "TTML/DFXP/ITT를 SRT로 변환 중...",
    "hi": "TTML/DFXP/ITT को SRT में परिवर्तित किया जा रहा है..."
}
CONVERTING_VTT = {
    "en": "Converting VTT to SRT...",
    "es": "Convirtiendo VTT a SRT...",
    "tr": "VTT uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 VTT 转换为 SRT...",
    "ru": "Преобразование VTT в SRT...",
    "pl": "Konwertowanie VTT na SRT...",
    "uk": "Перетворення VTT на SRT...",
    "ja": "VTT を SRT に変換しています...",
    "ko": "VTT를 SRT로 변환 중...",
    "hi": "VTT को SRT में परिवर्तित किया जा रहा है..."
}
CONVERTING_SBV = {
    "en": "Converting SBV to SRT...",
    "es": "Convirtiendo SBV a SRT...",
    "tr": "SBV uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 SBV 转换为 SRT...",
    "ru": "Преобразование SBV в SRT...",
    "pl": "Konwertowanie SBV na SRT...",
    "uk": "Перетворення SBV на SRT...",
    "ja": "SBV を SRT に変換しています...",
    "ko": "SBV를 SRT로 변환 중...",
    "hi": "SBV को SRT में परिवर्तित किया जा रहा है..."
}
CONVERTING_SUB = {
    "en": "Converting SUB to SRT...",
    "es": "Convirtiendo SUB a SRT...",
    "tr": "SUB uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 SUB 转换为 SRT...",
    "ru": "Преобразование SUB в SRT...",
    "pl": "Konwertowanie SUB na SRT...",
    "uk": "Перетворення SUB на SRT...",
    "ja": "SUB を SRT に変換しています...",
    "ko": "SUB를 SRT로 변환 중...",
    "hi": "SUB को SRT में परिवर्तित किया जा रहा है..."
}
CONVERTING_ASS = {
    "en": "Converting ASS/SSA to SRT...",
    "es": "Convirtiendo ASS/SSA a SRT...",
    "tr": "ASS/SSA uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 ASS/SSA 转换为 SRT...",
    "ru": "Преобразование ASS/SSA в SRT...",
    "pl": "Konwertowanie ASS/SSA na SRT...",
    "uk": "Перетворення ASS/SSA на SRT...",
    "ja": "ASS/SSA を SRT に変換しています...",
    "ko": "ASS/SSA를 SRT로 변환 중...",
    "hi": "ASS/SSA को SRT में परिवर्तित किया जा रहा है..."
}
CONVERTING_STL = {
    "en": "Converting STL to SRT...",
    "es": "Convirtiendo STL a SRT...",
    "tr": "STL uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 STL 转换为 SRT...",
    "ru": "Преобразование STL в SRT...",
    "pl": "Konwertowanie STL na SRT...",
    "uk": "Перетворення STL на SRT...",
    "ja": "STL を SRT に変換しています...",
    "ko": "STL을 SRT로 변환 중...",
    "hi": "STL को SRT में परिवर्तित किया जा रहा है..."
}
CONVERSION_NOT_SUPPORTED = {
    "en": "Error: Conversion for {file_extension} is not supported.",
    "es": "Error: La conversión para {file_extension} no está soportada.",
    "tr": "Hata: {file_extension} dönüştürme desteklenmiyor.",
    "zh": "错误：不支持 {file_extension} 的转换。",
    "ru": "Ошибка: Конвертация для {file_extension} не поддерживается.",
    "pl": "Błąd: Konwersja dla {file_extension} nie jest obsługiwana.",
    "uk": "Помилка: Перетворення для {file_extension} не підтримується.",
    "ja": "エラー：{file_extension} の変換はサポートされていません。",
    "ko": "오류: {file_extension} 변환이 지원되지 않습니다.",
    "hi": "त्रुटि: {file_extension} के लिए रूपांतरण समर्थित नहीं है।"
}
RETRY_ENCODING_MSG = {
    "en": "Previous sync failed. Retrying with pre-detected encodings...",
    "es": "La sincronización anterior falló. Reintentando con codificaciones pre-detectadas...",
    "tr": "Önceki senkronizasyon başarısız oldu. Önceden tespit edilen kodlamalarla yeniden deneniyor...",
    "zh": "上一次同步失败。正在使用预检测的编码重试...",
    "ru": "Предыдущая синхронизация не удалась. Повторная попытка с предварительно обнаруженными кодировками...",
    "pl": "Poprzednia synchronizacja nie powiodła się. Ponawianie z wstępnie wykrytymi kodowaniami...",
    "uk": "Попередня синхронізація не вдалася. Повторна спроба з попередньо виявленими кодуваннями...",
    "ja": "前回の同期に失敗しました。事前に検出されたエンコーディングで再試行しています...",
    "ko": "이전 동기화에 실패했습니다. 사전 감지된 인코딩으로 다시 시도 중...",
    "hi": "पिछला सिंक विफल रहा। पूर्व-निर्धारित एन्कोडिंग के साथ पुनः प्रयास कर रहा है..."
}
ALASS_SPEED_OPTIMIZATION_LOG = {
    "en": "Disabled: Speed optimization...",
    "es": "Deshabilitado: Optimización de velocidad...",
    "tr": "Devre dışı: Hız optimizasyonu...",
    "zh": "已禁用：速度优化...",
    "ru": "Отключено: Оптимизация скорости...",
    "pl": "Wyłączono: Optymalizacja prędkości...",
    "uk": "Вимкнено: Оптимізація швидкості...",
    "ja": "無効化：速度最適化...",
    "ko": "비활성화됨: 속도 최적화...",
    "hi": "अक्षम: गति अनुकूलन..."
}
ALASS_DISABLE_FPS_GUESSING_LOG = {
    "en": "Disabled: FPS guessing...",
    "es": "Deshabilitado: Adivinación de FPS...",
    "tr": "Devre dışı: FPS tahmini...",
    "zh": "已禁用：FPS 猜测...",
    "ru": "Отключено: Угадывание FPS...",
    "pl": "Wyłączono: Wykrywanie FPS...",
    "uk": "Вимкнено: Визначення FPS...",
    "ja": "無効化：FPS推測...",
    "ko": "비활성화됨: FPS 추측...",
    "hi": "अक्षम: FPS अनुमान..."
}
CHANGING_ENCODING_MSG = {
    "en": "The synchronized subtitle's encoding does not match the input subtitle's encoding. Changing from {synced_subtitle_encoding} encoding to {encoding_inc} encoding...",
    "es": "La codificación del subtítulo sincronizado no coincide con la codificación del subtítulo de entrada. Cambiando de codificación {synced_subtitle_encoding} a codificación {encoding_inc}...",
    "tr": "Senkronize altyazının kodlaması, girdi altyazının kodlamasıyla eşleşmiyor. {synced_subtitle_encoding} kodlamasından {encoding_inc} kodlamasına geçiliyor...",
    "zh": "同步字幕的编码与输入字幕的编码不匹配。正在从 {synced_subtitle_encoding} 编码更改为 {encoding_inc} 编码...",
    "ru": "Кодировка синхронизированных субтитров не совпадает с кодировкой входных субтитров. Изменение кодировки с {synced_subtitle_encoding} на {encoding_inc}...",
    "pl": "Kodowanie zsynchronizowanych napisów nie pasuje do kodowania napisów wejściowych. Zmiana kodowania z {synced_subtitle_encoding} na {encoding_inc}...",
    "uk": "Кодування синхронізованих субтитрів не збігається з кодуванням вхідних субтитрів. Зміна кодування з {synced_subtitle_encoding} на {encoding_inc}...",
    "ja": "同期した字幕のエンコーディングが入力字幕のエンコーディングと一致しません。エンコーディングを {synced_subtitle_encoding} から {encoding_inc} に変更しています...",
    "ko": "동기화된 자막의 인코딩이 입력 자막의 인코딩과 일치하지 않습니다. 인코딩을 {synced_subtitle_encoding}에서 {encoding_inc}로 변경 중...",
    "hi": "सिंक्रनाइज़ किए गए उपशीर्षक का एन्कोडिंग इनपुट उपशीर्षक के एन्कोडिंग से मेल नहीं खाता। एन्कोडिंग को {synced_subtitle_encoding} से {encoding_inc} में बदल रहा है..."
}
ENCODING_CHANGED_MSG = {
    "en": "Encoding changed successfully.",
    "es": "Codificación cambiada con éxito.",
    "tr": "Kodlama başarıyla değiştirildi.",
    "zh": "编码更改成功。",
    "ru": "Кодировка успешно изменена.",
    "pl": "Kodowanie zmienione pomyślnie.",
    "uk": "Кодування успішно змінено.",
    "ja": "エンコーディングが正常に変更されました。",
    "ko": "인코딩이 성공적으로 변경되었습니다.",
    "hi": "एन्कोडिंग सफलतापूर्वक बदल गया।"
}
SYNC_SUCCESS_COUNT = {
    "en": "Successfully synced {success_count} subtitle file(s).",
    "es": "Se sincronizaron correctamente {success_count} archivo(s) de subtítulos.",
    "tr": "{success_count} altyazı dosyası başarıyla senkronize edildi.",
    "zh": "成功同步了 {success_count} 个字幕文件。",
    "ru": "Успешно синхронизировано {success_count} файл(ов) субтитров.",
    "pl": "Pomyślnie zsynchronizowano {success_count} plik(ów) napisów.",
    "uk": "Успішно синхронізовано {success_count} файл(ів) субтитрів.",
    "ja": "正常に同期された字幕ファイル数：{success_count}",
    "ko": "성공적으로 동기화된 자막 파일 수: {success_count}",
    "hi": "सफलतापूर्वक सिंक्रनाइज़ किए गए उपशीर्षक फ़ाइल(एँ): {success_count}"
}
SYNC_FAILURE_COUNT = {
    "en": "Failed to sync {failure_count} subtitle file(s).",
    "es": "No se pudo sincronizar {failure_count} archivo(s) de subtítulos.",
    "tr": "{failure_count} altyazı dosyası senkronize edilemedi.",
    "zh": "未能同步 {failure_count} 个字幕文件。",
    "ru": "Не удалось синхронизировать {failure_count} файл(ов) субтитров.",
    "pl": "Nie udało się zsynchronizować {failure_count} plik(ów) napisów.",
    "uk": "Не вдалося синхронізувати {failure_count} файл(ів) субтитрів.",
    "ja": "同期に失敗した字幕ファイル数：{failure_count}",
    "ko": "동기화에 실패한 자막 파일 수: {failure_count}",
    "hi": "सिंक्रनाइज़ करने में विफल उपशीर्षक फ़ाइल(एँ): {failure_count}"
}
SYNC_FAILURE_COUNT_BATCH = {
    "en": "Failed to sync {failure_count} pair(s):",
    "es": "No se pudo sincronizar {failure_count} par(es):",
    "tr": "{failure_count} çift senkronize edilemedi:",
    "zh": "未能同步 {failure_count} 对：",
    "ru": "Не удалось синхронизировать {failure_count} пар(ы):",
    "pl": "Nie udało się zsynchronizować {failure_count} par(y):",
    "uk": "Не вдалося синхронізувати {failure_count} пар(и):",
    "ja": "同期に失敗したペア数：{failure_count}",
    "ko": "동기화에 실패한 쌍 수: {failure_count}",
    "hi": "सिंक्रनाइज़ करने में विफल जोड़ी(याँ): {failure_count}"
}
ERROR_CHANGING_ENCODING_MSG = {
    "en": "Error changing encoding: {error_message}\n",
    "es": "Error al cambiar la codificación: {error_message}\n",
    "tr": "Kodlama değiştirilirken hata: {error_message}\n",
    "zh": "更改编码时出错：{error_message}\n",
    "ru": "Ошибка при изменении кодировки: {error_message}\n",
    "pl": "Błąd podczas zmiany kodowania: {error_message}\n",
    "uk": "Помилка під час зміни кодування: {error_message}\n",
    "ja": "エンコーディングの変更エラー：{error_message}\n",
    "ko": "인코딩 변경 오류: {error_message}\n",
    "hi": "एन्कोडिंग बदलने में त्रुटि: {error_message}\n"
}
BACKUP_CREATED = {
    "en": "A backup of the existing subtitle file has been saved to: {output_subtitle_file}.",
    "es": "Se ha guardado una copia de seguridad del archivo de subtítulos existente en: {output_subtitle_file}.",
    "tr": "Mevcut altyazı dosyasının bir yedeği kaydedildi: {output_subtitle_file}.",
    "zh": "现有字幕文件的备份已保存到：{output_subtitle_file}。",
    "ru": "Резервная копия существующего файла субтитров сохранена в: {output_subtitle_file}.",
    "pl": "Kopia zapasowa istniejącego pliku napisów została zapisana do: {output_subtitle_file}.",
    "uk": "Резервну копію існуючого файлу субтитрів збережено до: {output_subtitle_file}.",
    "ja": "既存の字幕ファイルのバックアップが保存されました：{output_subtitle_file}。",
    "ko": "기존 자막 파일의 백업이 저장되었습니다: {output_subtitle_file}.",
    "hi": "मौजूदा उपशीर्षक फ़ाइल का बैकअप यहाँ सहेजा गया है: {output_subtitle_file}।"
}
CHECKING_SUBTITLE_STREAMS = {
    "en": "Checking the video for subtitle streams...",
    "es": "Verificando el video para flujos de subtítulos...",
    "tr": "Videodaki altyazı akışları kontrol ediliyor...",
    "zh": "正在检查视频的字幕流...",
    "ru": "Проверка видео на наличие потоков субтитров...",
    "pl": "Sprawdzanie strumieni napisów w wideo...",
    "uk": "Перевірка відео на наявність потоків субтитрів...",
    "ja": "ビデオの字幕ストリームを確認しています...",
    "ko": "비디오의 자막 스트림 확인 중...",
    "hi": "वीडियो के उपशीर्षक स्ट्रीम की जाँच कर रहा है..."
}
FOUND_COMPATIBLE_SUBTITLES = {
    "en": "Found {count} compatible subtitles to extract.\nExtracting subtitles to folder: {output_folder}...",
    "es": "Se encontraron {count} subtítulos compatibles para extraer.\nExtrayendo subtítulos en la carpeta: {output_folder}...",
    "tr": "Çıkartılacak {count} uyumlu altyazı bulundu.\nAltyazılar şu klasöre çıkartılıyor: {output_folder}...",
    "zh": "找到了 {count} 个兼容的字幕要提取。\n正在提取字幕到文件夹：{output_folder}...",
    "ru": "Найдено {count} совместимых субтитров для извлечения.\nИзвлечение субтитров в папку: {output_folder}...",
    "pl": "Znaleziono {count} kompatybilnych napisów do wyodrębnienia.\nWyodrębnianie napisów do folderu: {output_folder}...",
    "uk": "Знайдено {count} сумісних субтитрів для вилучення.\nВилучення субтитрів до папки: {output_folder}...",
    "ja": "抽出する互換性のある字幕が {count} 個見つかりました。\n字幕をフォルダに抽出しています：{output_folder}...",
    "ko": "추출할 호환 가능한 자막 {count}개를 찾았습니다.\n자막을 폴더로 추출 중: {output_folder}...",
    "hi": "निकालने के लिए {count} संगत उपशीर्षक मिले।\nउपशीर्षक को फ़ोल्डर में निकाल रहा है: {output_folder}..."
}
NO_COMPATIBLE_SUBTITLES = {
    "en": "No compatible subtitles found to extract.",
    "es": "No se encontraron subtítulos compatibles para extraer.",
    "tr": "Çıkartılacak uyumlu altyazı bulunamadı.",
    "zh": "找不到要提取的兼容字幕。",
    "ru": "Совместимые субтитры для извлечения не найдены.",
    "pl": "Nie znaleziono kompatybilnych napisów do wyodrębnienia.",
    "uk": "Не знайдено сумісних субтитрів для вилучення.",
    "ja": "抽出する互換性のある字幕が見つかりませんでした。",
    "ko": "추출할 호환 가능한 자막을 찾을 수 없습니다.",
    "hi": "निकालने के लिए कोई संगत उपशीर्षक नहीं मिला।"
}
SUCCESSFULLY_EXTRACTED = {
    "en": "Successfully extracted: {filename}.",
    "es": "Extraído exitosamente: {filename}.",
    "tr": "Başarıyla çıkartıldı: {filename}.",
    "zh": "成功提取：{filename}。",
    "ru": "Успешно извлечено: {filename}.",
    "pl": "Pomyślnie wyodrębniono: {filename}.",
    "uk": "Успішно вилучено: {filename}.",
    "ja": "正常に抽出されました：{filename}。",
    "ko": "성공적으로 추출됨: {filename}.",
    "hi": "सफलतापूर्वक निकाला गया: {filename}।"
}
CHOOSING_BEST_SUBTITLE = {
    "en": "Selecting the best subtitle for syncing...",
    "es": "Seleccionando el mejor subtítulo para sincronizar...",
    "tr": "Senkronizasyon için en iyi altyazı seçiliyor...",
    "zh": "选择最佳字幕进行同步...",
    "ru": "Выбор лучшего субтитра для синхронизации...",
    "pl": "Wybieranie najlepszego napisu do synchronizacji...",
    "uk": "Вибір найкращого субтитру для синхронізації...",
    "ja": "同期に最適な字幕を選択しています...",
    "ko": "동기화에 가장 적합한 자막 선택 중...",
    "hi": "सिंकिंग के लिए सर्वश्रेष्ठ उपशीर्षक का चयन कर रहा है..."
}
CHOSEN_SUBTITLE = {
    "en": "Selected: {filename} with timestamp difference: {score}",
    "es": "Seleccionado: {filename} con diferencia de marca de tiempo: {score}",
    "tr": "Seçildi: {filename}, zaman damgası farkı: {score}",
    "zh": "已选择：{filename}，时间戳差异：{score}",
    "ru": "Выбрано: {filename} с разницей во времени: {score}",
    "pl": "Wybrano: {filename} z różnicą czasową: {score}",
    "uk": "Вибрано: {filename} з різницею у часі: {score}",
    "ja": "選択されました：{filename}、タイムスタンプの差：{score}",
    "ko": "선택됨: {filename}, 타임스탬프 차이: {score}",
    "hi": "चयनित: {filename} समय अंतर के साथ: {score}"
}
FAILED_TO_EXTRACT_SUBTITLES = {
    "en": "Failed to extract subtitles. Error: {error}",
    "es": "No se pudieron extraer los subtítulos. Error: {error}",
    "tr": "Altyazılar çıkarılamadı. Hata: {error}",
    "zh": "提取字幕失败。错误：{error}",
    "ru": "Не удалось извлечь субтитры. Ошибка: {error}",
    "pl": "Nie udało się wyodrębnić napisów. Błąd: {error}",
    "uk": "Не вдалося вилучити субтитри. Помилка: {error}",
    "ja": "字幕の抽出に失敗しました。エラー：{error}",
    "ko": "자막을 추출하지 못했습니다. 오류: {error}",
    "hi": "उपशीर्षक निकालने में विफल। त्रुटि: {error}"
}
USED_THE_LONGEST_SUBTITLE = {
    "en": "Used the longest subtitle file because parse_timestamps failed.",
    "es": "Se usó el archivo de subtítulos más largo porque parse_timestamps falló.",
    "tr": "parse_timestamps başarısız olduğu için en uzun altyazı dosyası kullanıldı.",
    "zh": "使用最长的字幕文件，因为 parse_timestamps 失败。",
    "ru": "Использован самый длинный файл субтитров, потому что parse_timestamps завершился с ошибкой.",
    "pl": "Użyto najdłuższego pliku napisów, ponieważ parse_timestamps nie powiodło się.",
    "uk": "Використано найдовший файл субтитрів, оскільки parse_timestamps не вдалося.",
    "ja": "parse_timestamps が失敗したため、最も長い字幕ファイルを使用しました。",
    "ko": "parse_timestamps가 실패했기 때문에 가장 긴 자막 파일을 사용했습니다.",
    "hi": "parse_timestamps विफल होने के कारण सबसे लंबे उपशीर्षक फ़ाइल का उपयोग किया गया।"
}
DELETING_EXTRACTED_SUBTITLE_FOLDER = {
    "en": "Deleting the extracted subtitles folder...",
    "es": "Eliminando la carpeta de subtítulos extraídos...",
    "tr": "Çıkarılan altyazılar klasörü siliniyor...",
    "zh": "删除提取的字幕文件夹...",
    "ru": "Удаление папки извлеченных субтитров...",
    "pl": "Usuwanie folderu wyodrębnionych napisów...",
    "uk": "Видалення папки вилучених субтитрів...",
    "ja": "抽出された字幕フォルダを削除しています...",
    "ko": "추출된 자막 폴더 삭제 중...",
    "hi": "निकाले गए उपशीर्षक फ़ोल्डर को हटा रहा है..."
}
DELETING_CONVERTED_SUBTITLE = {
    "en": "Deleting the converted subtitle file...",
    "es": "Eliminando el archivo de subtítulos convertido...",
    "tr": "Dönüştürülmüş altyazı dosyası siliniyor...",
    "zh": "正在检查视频的字幕流...",
    "ru": "Удаление преобразованного файла субтитров...",
    "pl": "Usuwanie przekonwertowanego pliku napisów...",
    "uk": "Видалення перетвореного файлу субтитрів...",
    "ja": "変換された字幕ファイルを削除しています...",
    "ko": "변환된 자막 파일 삭제 중...",
    "hi": "परिवर्तित उपशीर्षक फ़ाइल को हटा रहा है..."
}
ADDED_FILES_TEXT = {
    "en": "Added {added_files} files",
    "es": "Agregado {added_files} archivos",
    "tr": "{added_files} dosya eklendi",
    "zh": "添加了 {added_files} 个文件",
    "ru": "Добавлено {added_files} файлов",
    "pl": "Dodano {added_files} plików",
    "uk": "Додано {added_files} файлів",
    "ja": "{added_files} 個のファイルが追加されました",
    "ko": "{added_files}개의 파일이 추가되었습니다",
    "hi": "{added_files} फ़ाइलें जोड़ी गईं"
}
SKIPPED_DUPLICATE_FILES_TEXT = {
    "en": "Skipped {skipped_files} duplicate files",
    "es": "Omitido {skipped_files} archivos duplicados",
    "tr": "{skipped_files} yinelenen dosya atlandı",
    "zh": "跳过 {skipped_files} 个重复文件",
    "ru": "Пропущено {skipped_files} дублированных файлов",
    "pl": "Pominięto {skipped_files} zduplikowanych plików",
    "uk": "Пропущено {skipped_files} дубльованих файлів",
    "ja": "{skipped_files} 個の重複ファイルがスキップされました",
    "ko": "{skipped_files}개의 중복 파일이 건너뛰어졌습니다",
    "hi": "{skipped_files} डुप्लिकेट फ़ाइलें छोड़ी गईं"
}
SKIPPED_OTHER_LIST_FILES_TEXT = {
    "en": "Skipped {duplicate_in_other} files already in other list",
    "es": "Omitido {duplicate_in_other} archivos ya en la otra lista",
    "tr": "Diğer listede bulunan {duplicate_in_other} dosya atlandı",
    "zh": "跳过 {duplicate_in_other} 个已在其他列表中的文件",
    "ru": "Пропущено {duplicate_in_other} файлов, уже находящихся в другом списке",
    "pl": "Pominięto {duplicate_in_other} plików już znajdujących się na innej liście",
    "uk": "Пропущено {duplicate_in_other} файлів, які вже є в іншому списку",
    "ja": "他のリストに既にある {duplicate_in_other} 個のファイルがスキップされました",
    "ko": "다른 목록에 이미 있는 {duplicate_in_other}개의 파일이 건너뛰어졌습니다",
    "hi": "अन्य सूची में पहले से मौजूद {duplicate_in_other} फ़ाइलें छोड़ी गईं"
}
SKIPPED_SEASON_EPISODE_DUPLICATES_TEXT = {
    "en": "Skipped {len} files with duplicate season/episode numbers",
    "es": "Omitido {len} archivos con números de temporada/episodio duplicados",
    "tr": "Aynı sezon/bölüm numaralarına sahip {len} dosya atlandı",
    "zh": "跳过 {len} 个具有重复季/集编号的文件",
    "ru": "Пропущено {len} файлов с дублирующимися номерами сезона/эпизода",
    "pl": "Pominięto {len} plików z duplikatami numerów sezonu/odcinka",
    "uk": "Пропущено {len} файлів з дубльованими номерами сезону/епізоду",
    "ja": "シーズン/エピソード番号が重複している {len} 個のファイルがスキップされました",
    "ko": "중복된 시즌/에피소드 번호가 있는 {len}개의 파일이 건너뛰어졌습니다",
    "hi": "डुप्लिकेट सीजन/एपिसोड नंबर वाली {len} फ़ाइलें छोड़ी गईं"
}
SKIPPED_INVALID_FORMAT_FILES_TEXT = {
    "en": "Skipped {len} files without valid episode format",
    "es": "Omitido {len} archivos sin formato de episodio válido",
    "tr": "Geçerli bölüm formatı olmayan {len} dosya atlandı",
    "zh": "跳过 {len} 个没有有效集格式的文件",
    "ru": "Пропущено {len} файлов без действительного формата эпизода",
    "pl": "Pominięto {len} plików bez prawidłowego formatu odcinka",
    "uk": "Пропущено {len} файлів без дійсного формату епізоду",
    "ja": "有効なエピソード形式がない {len} 個のファイルがスキップされました",
    "ko": "유효한 에피소드 형식이 없는 {len}개의 파일이 건너뛰어졌습니다",
    "hi": "मान्य एपिसोड प्रारूप के बिना {len} फ़ाइलें छोड़ी गईं"
}
NO_FILES_SELECTED = {
    "en": "No files selected.",
    "es": "No se seleccionaron archivos.",
    "tr": "Dosya seçilmedi.",
    "zh": "未选择文件。",
    "ru": "Файлы не выбраны.",
    "pl": "Nie wybrano plików.",
    "uk": "Файли не вибрано.",
    "ja": "ファイルが選択されていません。",
    "ko": "파일이 선택되지 않았습니다.",
    "hi": "कोई फ़ाइल चयनित नहीं है।"
}
NO_ITEM_SELECTED_TO_REMOVE = {
    "en": "No item selected to remove.",
    "es": "No se seleccionó ningún elemento para eliminar.",
    "tr": "Kaldırmak için öğe seçilmedi.",
    "zh": "未选择要删除的项目。",
    "ru": "Не выбран элемент для удаления.",
    "pl": "Nie wybrano elementu do usunięcia.",
    "uk": "Не вибрано елемент для видалення.",
    "ja": "削除する項目が選択されていません。",
    "ko": "제거할 항목이 선택되지 않았습니다.",
    "hi": "हटाने के लिए कोई आइटम चयनित नहीं है।"
}
NO_FILES_SELECTED_TO_SHOW_PATH = {
    "en": "No file selected to show path.",
    "es": "No se seleccionó ningún archivo para mostrar la ruta.",
    "tr": "Yolu göstermek için dosya seçilmedi.",
    "zh": "未选择要显示路径的文件。",
    "ru": "Файл не выбран для отображения пути.",
    "pl": "Nie wybrano pliku do pokazania ścieżki.",
    "uk": "Файл не вибрано для відображення шляху.",
    "ja": "パスを表示するファイルが選択されていません。",
    "ko": "경로를 표시할 파일이 선택되지 않았습니다.",
    "hi": "पथ दिखाने के लिए कोई फ़ाइल चयनित नहीं है।"
}
REMOVED_ITEM = {
    "en": "Removed item.",
    "es": "Elemento eliminado.",
    "tr": "Öğe kaldırıldı.",
    "zh": "已删除项目。",
    "ru": "Элемент удален.",
    "pl": "Usunięto element.",
    "uk": "Елемент видалено.",
    "ja": "項目が削除されました。",
    "ko": "항목이 제거되었습니다.",
    "hi": "आइटम हटा दिया गया।"
}
FILES_MUST_CONTAIN_PATTERNS = {
    "en": "Files must contain patterns like S01E01, 1x01 etc.",
    "es": "Los archivos deben contener patrones como S01E01, 1x01 etc.",
    "tr": "Dosyalar S01E01, 1x01 vb. kalıplar içermelidir.",
    "zh": "文件必须包含 S01E01、1x01 等模式。",
    "ru": "Файлы должны содержать шаблоны типа S01E01, 1x01 и т. д.",
    "pl": "Pliki muszą zawierać wzorce takie jak S01E01, 1x01 itp.",
    "uk": "Файли повинні містити шаблони, такі як S01E01, 1x01 тощо.",
    "ja": "ファイルには S01E01、1x01 などのパターンが含まれている必要があります。",
    "ko": "파일에는 S01E01, 1x01 등의 패턴이 포함되어야 합니다.",
    "hi": "फ़ाइलों में S01E01, 1x01 आदि जैसे पैटर्न होने चाहिए।"
}
NO_VALID_SUBTITLE_FILES = {
    "en": "No valid files found.",
    "es": "No se encontraron archivos de subtítulos válidos.",
    "tr": "Geçerli altyazı dosyası bulunamadı.",
    "zh": "找不到有效的字幕文件。",
    "ru": "Действительные файлы субтитров не найдены.",
    "pl": "Nie znaleziono prawidłowych plików napisów.",
    "uk": "Не знайдено дійсних файлів субтитрів.",
    "ja": "有効な字幕ファイルが見つかりませんでした。",
    "ko": "유효한 자막 파일을 찾을 수 없습니다.",
    "hi": "कोई मान्य उपशीर्षक फ़ाइल नहीं मिली।"
}
NO_SUBTITLE_PAIRS_TO_PROCESS = {
    "en": "No pairs to process.",
    "es": "No hay pares para procesar.",
    "tr": "İşlenecek çift yok.",
    "zh": "没有要处理的对。",
    "ru": "Нет пар для обработки.",
    "pl": "Brak par do przetworzenia.",
    "uk": "Немає пар для обробки.",
    "ja": "処理するペアがありません。",
    "ko": "처리할 쌍이 없습니다.",
    "hi": "प्रक्रिया करने के लिए कोई जोड़ी नहीं है।"
}
NO_MATCHING_SUBTITLE_PAIRS_FOUND = {
    "en": "No matching pairs found.",
    "es": "No se encontraron pares coincidentes.",
    "tr": "Eşleşen çift bulunamadı.",
    "zh": "找不到匹配的对。",
    "ru": "Совпадающие пары не найдены.",
    "pl": "Nie znaleziono pasujących par.",
    "uk": "Не знайдено відповідних пар.",
    "ja": "一致するペアが見つかりませんでした。",
    "ko": "일치하는 쌍을 찾을 수 없습니다.",
    "hi": "कोई मेल खाने वाली जोड़ी नहीं मिली।"
}
NO_VALID_SUBTITLE_PAIRS_TO_PROCESS = {
    "en": "No valid pairs to process.",
    "es": "No hay pares válidos para procesar.",
    "tr": "İşlenecek geçerli çift yok.",
    "zh": "没有有效的对要处理。",
    "ru": "Нет действительных пар для обработки.",
    "pl": "Brak prawidłowych par do przetworzenia.",
    "uk": "Немає дійсних пар для обробки.",
    "ja": "処理する有効なペアがありません。",
    "ko": "처리할 유효한 쌍이 없습니다.",
    "hi": "प्रक्रिया करने के लिए कोई मान्य जोड़ी नहीं है।"
}
for name, obj in list(globals().items()):
    if isinstance(obj, dict) and name != "TranslationDict":
        globals()[name] = TranslationDict(obj)