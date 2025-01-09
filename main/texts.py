class TranslationDict(dict):
    def __missing__(self, key):
        return self.get("en", "")
PROGRAM_NAME = "AutoSubSync"
TOOLTIP_SAVE_TO_DESKTOP = {
    "en": "Check this box if you want to save the new subtitle to your Desktop. If unchecked, it will be saved in the original subtitle's folder.",
    "ess": "Marque esta casilla si desea guardar el nuevo subtítulo en su escritorio. Si no está marcado, se guardará en la carpeta del subtítulo original.",
    "tr": "Yeni altyazıyı masaüstüne kaydetmek istiyorsanız bu kutuyu işaretleyin. İşaretlenmezse, orijinal altyazının klasörüne kaydedilecektir.",
    "zh": "如果您想将新字幕保存到桌面，请选中此框。如果未选中，它将保存在原始字幕的文件夹中。",
    "ru": "Если вы хотите сохранить новый субтитр на рабочем столе, установите этот флажок. Если флажок не установлен, он будет сохранен в папке оригинальных субтитров."
}
TOOLTIP_REPLACE_ORIGINAL = {
    "en": "Check this box if you want to replace the original subtitle file with the new one. Please be careful. It will overwrite the current subtitle.",
    "es": "Marque esta casilla si desea reemplazar el archivo de subtítulos original con el nuevo. Por favor, tenga cuidado. Sobrescribirá el subtítulo actual.",
    "tr": "Orijinal altyazı dosyasını yenisiyle değiştirmek istiyorsanız bu kutuyu işaretleyin. Lütfen dikkatli olun. Mevcut altyazının üzerine yazacaktır.",
    "zh": "如果您想用新的字幕文件替换原始字幕文件，请选中此框。请小心。它将覆盖当前字幕。",
    "ru": "Если вы хотите заменить оригинальный файл субтитров на новый, установите этот флажок. Пожалуйста, будьте осторожны. Он перезапишет текущий субтитр."
}
TOOLTIP_GSS = {
    "en": "--gss: Use golden-section search to find the optimal ratio between video and subtitle framerates (by default, only a few common ratios are evaluated)",
    "es": "--gss: Utilice la búsqueda de sección áurea para encontrar la proporción óptima entre las tasas de fotogramas de video y subtítulos (por defecto, solo se evalúan algunas proporciones comunes)",
    "tr": "--gss: Video ve altyazı kare hızları arasındaki en uygun oranı bulmak için altın oran aramasını kullanın (varsayılan olarak, yalnızca birkaç yaygın oran değerlendirilir)",
    "zh": "--gss: 使用黄金分割搜索来找到视频和字幕帧速率之间的最佳比例（默认情况下，仅评估一些常见的比例）",
    "ru": "--gss: Используйте поиск золотого сечения для нахождения оптимального соотношения между частотами кадров видео и субтитров (по умолчанию оцениваются только несколько общих соотношений)"
}
TOOLTIP_VAD = {
    "en": "--vad=auditok: Auditok can sometimes work better in the case of low-quality audio than WebRTC's VAD. Auditok does not specifically detect voice, but instead detects all audio; this property can yield suboptimal syncing behavior when a proper VAD can work well, but can be effective in some cases.",
    "es": "--vad=auditok: Auditok a veces puede funcionar mejor en el caso de audio de baja calidad que el VAD de WebRTC. Auditok no detecta específicamente la voz, sino que detecta todo el audio; esta propiedad puede producir un comportamiento de sincronización subóptimo cuando un VAD adecuado puede funcionar bien, pero puede ser efectivo en algunos casos.",
    "tr": "--vad=auditok: Auditok, düşük kaliteli ses durumunda bazen WebRTC'nin VAD'sinden daha iyi çalışabilir. Auditok, özellikle sesi algılamaz, bunun yerine tüm sesleri algılar; bu özellik, uygun bir VAD'nin iyi çalışabileceği durumlarda optimal olmayan senkronizasyon davranışına neden olabilir, ancak bazı durumlarda etkili olabilir.",
    "zh": "--vad=auditok: 在低质量音频的情况下，Auditok 有时比 WebRTC 的 VAD 更有效。Auditok 不专门检测语音，而是检测所有音频；这种特性在适当的 VAD 可以正常工作时可能会产生次优的同步行为，但在某些情况下可能会有效。",
    "ru": "--vad=auditok: Auditok иногда может работать лучше в случае низкокачественного аудио, чем VAD WebRTC. Auditok не определяет голос, а вместо этого определяет весь аудио; это свойство может привести к субоптимальному поведению синхронизации, когда правильный VAD может работать хорошо, но может быть эффективным в некоторых случаях."

}
TOOLTIP_FRAMERATE = {
    "en": "--no-fix-framerate: If specified, ffsubsync will not attempt to correct a framerate mismatch between reference and subtitles. This can be useful when you know that the video and subtitle framerates are same, only the subtitles are out of sync.",
    "es": "--no-fix-framerate: Si se especifica, ffsubsync no intentará corregir una discrepancia de velocidad de fotogramas entre la referencia y los subtítulos. Esto puede ser útil cuando sabes que las tasas de fotogramas de video y subtítulos son las mismas, solo los subtítulos están desincronizados.",
    "tr": "--no-fix-framerate: Belirtilirse, ffsubsync referans ve altyazılar arasındaki kare hızı uyumsuzluğunu düzeltmeye çalışmaz. Bu, video ve altyazı kare hızlarının aynı olduğunu bildiğinizde, yalnızca altyazıların senkronize olmadığında yararlı olabilir.",
    "zh": "--no-fix-framerate: 如果指定，ffsubsync 将不会尝试纠正参考和字幕之间的帧速率不匹配。当您知道视频和字幕帧速率相同时，这可能很有用，只是字幕不同步。",
    "ru": "--no-fix-framerate: Если указано, ffsubsync не будет пытаться исправить несоответствие частоты кадров между эталонным видео и субтитрами. Это может быть полезно, когда вы знаете, что частоты кадров видео и субтитров совпадают, только субтитры не синхронизированы."
}
TOOLTIP_ALASS_SPEED_OPTIMIZATION = {
    "en": "--speed optimization 0: Disable speed optimization for better accuracy. This will increase the processing time.",
    "es": "--speed optimization 0: Deshabilite la optimización de velocidad para una mejor precisión. Esto aumentará el tiempo de procesamiento.",
    "tr": "--speed optimization 0: Daha iyi doğruluk için hız optimizasyonunu devre dışı bırakın. Bu, işlem süresini artıracaktır.",
    "zh": "--speed optimization 0: 禁用速度优化以获得更高的准确性。这将增加处理时间。",
    "ru": "--speed optimization 0: Отключить оптимизацию скорости для лучшей точности. Это увеличит время обработки."
}
TOOLTIP_ALASS_DISABLE_FPS_GUESSING = {
    "en": "--disable-fps-guessing: Disables guessing and correcting of framerate differences between reference file and input file.",
    "es": "--disable-fps-guessing: Deshabilita la adivinación y corrección de diferencias de velocidad de fotogramas entre el archivo de referencia y el archivo de entrada.",
    "tr": "--disable-fps-guessing: Referans dosya ile giriş dosyası arasındaki kare hızı farklarını tahmin etmeyi ve düzeltmeyi devre dışı bırakır.",
    "zh": "--disable-fps-guessing: 禁用参考文件和输入文件之间帧速率差异的猜测和校正。",
    "ru": "--disable-fps-guessing: Отключает угадывание и коррекцию различий частоты кадров между файлом справки и входным файлом."
}
TOOLTIP_TEXT_ACTION_MENU_AUTO = {
    "en": "Choose what to do with the synchronized subtitle file(s). (Existing subtitle files will be backed up in the same folder, if they need to be replaced.)",
    "es": "Elija qué hacer con el/los archivo(s) de subtítulos sincronizados. (Los archivos de subtítulos existentes se respaldarán en la misma carpeta, si necesitan ser reemplazados.)",
    "tr": "Senkronize edilmiş altyazı dosyası/dosyaları ile ne yapılacağını seçin. (Mevcut altyazı dosyaları değiştirilmesi gerekiyorsa aynı klasörde yedeklenecektir.)",
    "zh": "选择如何处理同步的字幕文件。（如果需要替换现有字幕文件，它们将在同一文件夹中备份。）",
    "ru": "Выберите, что делать с синхронизированным(и) файлом(ами) субтитров. (Существующие файлы субтитров будут скопированы в ту же папку, если их нужно заменить.)"
}
TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO = {
    "en": "Select the tool to use for synchronization.",
    "es": "Seleccione la herramienta a utilizar para la sincronización.",
    "tr": "Senkronizasyon için kullanılacak aracı seçin.",
    "zh": "选择用于同步的工具。",
    "ru": "Выберите инструмент для синхронизации."
}
UPDATE_AVAILABLE_TITLE = {
    "en": "Update Available",
    "es": "Actualización Disponible",
    "tr": "Güncelleme Mevcut",
    "zh": "有可用更新",
    "ru": "Доступно обновление"
}
UPDATE_AVAILABLE_TEXT = {
    "en": "A new version ({latest_version}) is available. Do you want to update?",
    "es": "Una nueva versión ({latest_version}) está disponible. ¿Quieres actualizar?",
    "tr": "Yeni bir sürüm ({latest_version}) mevcut. Güncellemek istiyor musunuz?",
    "zh": "有新版本 ({latest_version}) 可用。您想更新吗？",
    "ru": "Доступна новая версия ({latest_version}). Хотите обновить?"
}
NOTIFY_ABOUT_UPDATES_TEXT = {
    "en": "Notify about updates",
    "es": "Notificar sobre actualizaciones",
    "tr": "Güncellemeler hakkında bilgilendir",
    "zh": "通知关于更新",
    "ru": "Уведомлять о обновлениях"
}
LANGUAGE_LABEL_TEXT = {
    "en": "Language",
    "es": "Idioma",
    "tr": "Dil",
    "zh": "语言",
    "ru": "Язык"
}
# TEXT SHOULD BE SHORT
TAB_AUTOMATIC_SYNC = {
    "en": 'Automatic Sync',
    "es": 'Sinc. Automática',
    "tr": 'Otomatik Senkr.',
    "zh": '自动同步',
    "ru": 'Автомат. синхр.'
}
# TEXT SHOULD BE SHORT
TAB_MANUAL_SYNC = {
    "en": 'Manual Sync',
    "es": 'Sinc. Manual',
    "tr": 'Manuel Senk.',
    "zh": '手动同步',
    "ru": 'Ручная синхр.'
}
CANCEL_TEXT = {
    "en": 'Cancel',
    "es": 'Cancelar',
    "tr": 'İptal',
    "zh": '取消',
    "ru": 'Отмена'
}
GENERATE_AGAIN_TEXT = {
    "en": 'Generate Again',
    "es": 'Generar de Nuevo',
    "tr": 'Tekrar Oluştur',
    "zh": '再次生成',
    "ru": 'Сгенерировать снова'
}
GO_BACK = {
    "en": 'Go Back',
    "es": 'Regresar',
    "tr": 'Geri Dön',
    "zh": '返回',
    "ru": 'Вернуться'
}
BATCH_MODE_TEXT = {
    "en": 'Batch Mode',
    "es": 'Modo por Lotes',
    "tr": 'Toplu Mod',
    "zh": '批处理模式',
    "ru": 'Пакетный режим'
}
NORMAL_MODE_TEXT = {
    "en": 'Normal Mode',
    "es": 'Modo Normal',
    "tr": 'Normal Mod',
    "zh": '正常模式',
    "ru": 'Обычный режим'
}
# TEXT SHOULD BE SHORT
START_AUTOMATIC_SYNC_TEXT = {
    "en": 'Start Automatic Sync',
    "es": 'Iniciar Sinc. Automática',
    "tr": 'Otomatik Senkr. Başlat',
    "zh": "开始自动同步",
    "ru": 'Начать автосинхронизацию'
}
# TEXT SHOULD BE SHORT
START_BATCH_SYNC_TEXT = {
    "en": 'Start Batch Sync',
    "es": 'Iniciar Sincr. por Lotes',
    "tr": 'Toplu Senkr. Başlat',
    "zh": "开始批量同步",
    "ru": 'Начать пакетную синхр.'
}
BATCH_INPUT_TEXT = {
    "en": "Drag and drop multiple files/folders here or click to browse.\n\n(Videos and subtitles that have the same filenames will be paired automatically. You need to pair others manually.)",
    "es": "Arrastre y suelte varios archivos/carpetas aquí o haga clic para buscar.\n\n(Los videos y subtítulos que tienen los mismos nombres de archivo se emparejarán automáticamente. Debe emparejar otros manualmente.)",
    "tr": "Birden fazla dosya/klasörü buraya sürükleyip bırakın veya göz atmak için tıklayın.\n\n(Aynı dosya adlarına sahip videolar ve altyazılar otomatik olarak eşleştirilecektir. Diğerlerini manuel olarak eşleştirmeniz gerekir.)",
    "zh": "将多个文件/文件夹拖放到此处或点击浏览。\n\n(具有相同文件名的视频和字幕将自动配对。您需要手动配对其他文件。)",
    "ru": "Перетащите несколько файлов/папок сюда или нажмите, чтобы выбрать.\n\n(Видео и субтитры с одинаковыми именами файлов будут автоматически сопоставлены. Для других вам нужно будет сопоставить вручную.)"
}
BATCH_INPUT_LABEL_TEXT = {
    "en": "Batch Processing Mode",
    "es": "Modo de Procesamiento por Lotes",
    "tr": "Toplu İşleme Modu",
    "zh": "批处理模式",
    "ru": "Режим пакетной обработки"
}
SHIFT_SUBTITLE_TEXT = {
    "en": 'Shift Subtitle',
    "es": 'Desplazar Subtítulo',
    "tr": 'Altyazıyı Kaydır',
    "zh": '移位字幕',
    "ru": 'Сдвиг субтитров'
}
LABEL_SHIFT_SUBTITLE = {
    "en": "Shift subtitle by (ms):",
    "es": "Desplazar subtítulo (ms):",
    "tr": "Altyazıyı kaydır (ms):",
    "zh": "移位字幕（毫秒）：",
    "ru": "Сдвинуть субтитры на (мс):"
}
REPLACE_ORIGINAL_TITLE = {
    "en": "Subtitle Change Confirmation",
    "es": "Confirmación de Cambio de Subtítulo",
    "tr": "Altyazı Değişikliği Onayı",
    "zh": "字幕更改确认",
    "ru": "Подтверждение изменения субтитров"
}
REPLACE_ORIGINAL_TEXT = {
    "en": "Adjusting again by {milliseconds}ms, will make a total difference of {total_shifted}ms. Proceed?",
    "es": "Ajustar nuevamente por {milliseconds}ms, hará una diferencia total de {total_shifted}ms. ¿Proceder?",
    "tr": "{milliseconds}ms kadar yeniden ayarlamak, toplamda {total_shifted}ms fark yaratacaktır. Devam edilsin mi?",
    "zh": "再次调整 {milliseconds} 毫秒，总共将差 {total_shifted} 毫秒。继续吗？",
    "ru": "Повторная настройка на {milliseconds} мс создаст общую разницу в {total_shifted} мс. Продолжить?"
}
FILE_EXISTS_TITLE = {
    "en": "File Exists",
    "es": "El Archivo Existe",
    "tr": "Dosya Mevcut",
    "zh": "文件已存在",
    "ru": "Файл существует"
}
FILE_EXISTS_TEXT = {
    "en": "A file with the name '{filename}' already exists. Do you want to replace it?",
    "es": "Un archivo con el nombre '{filename}' ya existe. ¿Desea reemplazarlo?",
    "tr": "'{filename}' adında bir dosya zaten var. Değiştirmek istiyor musunuz?",
    "zh": "名为 '{filename}' 的文件已存在。您要替换它吗？",
    "ru": "Файл с именем '{filename}' уже существует. Хотите заменить его?"
}
ALREADY_SYNCED_FILES_TITLE = {
    "en": "Already Synced Files Detected",
    "es": "Archivos Ya Sincronizados Detectados",
    "tr": "Zaten Senkronize Edilmiş Dosyalar Tespit Edildi",
    "zh": "检测到已同步的文件",
    "ru": "Обнаружены уже синхронизированные файлы"
}
ALREADY_SYNCED_FILES_MESSAGE = {
    "en": "Detected {count} subtitle(s) already synced, because there are subtitles that have 'autosync_' prefix in the same folder with same filenames. Do you want to skip processing them?\n\n(Even if you say no, your existing subtitles will not be overwritten. The subtitle will be saved with different name.)",
    "es": "Se detectaron {count} subtítulo(s) ya sincronizados, porque hay subtítulos que tienen el prefijo 'autosync_' en la misma carpeta con los mismos nombres de archivo. ¿Desea omitir su procesamiento?\n\n(Incluso si dice que no, sus subtítulos existentes no se sobrescribirán. El subtítulo se guardará con un nombre diferente.)",
    "tr": "Aynı klasörde aynı dosya adlarına sahip 'autosync_' öneki olan altyazılar olduğu için {count} altyazı zaten senkronize edilmiş olarak tespit edildi. İşlemeyi atlamak istiyor musunuz?\n\n(Hayır deseniz bile, mevcut altyazılarınız üzerine yazılmayacaktır. Altyazı farklı bir adla kaydedilecektir.)",
    "zh": "检测到 {count} 个字幕已同步，因为在同一文件夹中有带有 'autosync_' 前缀的字幕，文件名相同。您要跳过处理它们吗？\n\n（即使您说不，现有字幕也不会被覆盖。字幕将以不同的名称保存。）",
    "ru": "Обнаружено {count} субтитров уже синхронизировано, потому что есть субтитры с префиксом 'autosync_' в той же папке с теми же именами файлов. Хотите пропустить их обработку?\n\n(Даже если вы скажете нет, ваши существующие субтитры не будут перезаписаны. Субтитр будет сохранен под другим именем.)"
}
SUBTITLE_INPUT_TEXT = {
    "en": "Drag and drop the unsynchronized subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de subtítulos no sincronizado aquí o haga clic para buscar.",
    "tr": "Senkronize edilmemiş altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın.",
    "zh": "将未同步的字幕文件拖放到此处或点击浏览。",
    "ru": "Перетащите несинхронизированный файл субтитров сюда или нажмите, чтобы выбрать."
}
VIDEO_INPUT_TEXT = {
    "en": "Drag and drop video or reference subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de video o subtítulos de referencia aquí o haga clic para buscar.",
    "tr": "Video veya referans altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın.",
    "zh": "将视频或参考字幕文件拖放到此处或点击浏览。",
    "ru": "Перетащите видео или файл справочных субтитров сюда или нажмите, чтобы выбрать."
}
LABEL_DROP_BOX = {
    "en": "Drag and drop subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de subtítulos aquí o haga clic para buscar.",
    "tr": "Altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın.",
    "zh": "将字幕文件拖放到此处或点击浏览。",
    "ru": "Перетащите файл субтитров сюда или нажмите, чтобы выбрать."
}
WARNING = {
    "en": "Warning",
    "es": "Advertencia",
    "tr": "Uyarı",
    "zh": "警告",
    "ru": "Предупреждение"
}
CONFIRM_RESET_MESSAGE = {
    "en": "Are you sure you want to reset settings to default values?",
    "es": "¿Está seguro de que desea restablecer la configuración a los valores predeterminados?",
    "tr": "Ayarları varsayılan değerlere sıfırlamak istediğinizden emin misiniz?",
    "zh": "您确定要将设置重置为默认值吗？",
    "ru": "Вы уверены, что хотите сбросить настройки на значения по умолчанию?"
}
TOGGLE_KEEP_CONVERTED_SUBTITLES_WARNING = {
    "en": 'Subtitles with "converted_subtitlefilename" in the output folder will be deleted automatically. Do you want to continue?',
    "es": 'Los subtítulos con "converted_subtitlefilename" en la carpeta de salida se eliminarán automáticamente. ¿Desea continuar?',
    "tr": 'Çıktı klasöründe "converted_subtitlefilename" olan altyazılar otomatik olarak silinecektir. Devam etmek istiyor musunuz?',
    "zh": '输出文件夹中带有 "converted_subtitlefilename" 的字幕将自动删除。您要继续吗？',
    "ru": 'Субтитры с "converted_subtitlefilename" в папке вывода будут автоматически удалены. Хотите продолжить?'
}
TOGGLE_KEEP_EXTRACTED_SUBTITLES_WARNING = {
    "en": 'Folders with "extracted_subtitles_videofilename" in the output folder will be deleted automatically. Do you want to continue?',
    "es": 'Las carpetas con "extracted_subtitles_videofilename" en la carpeta de salida se eliminarán automáticamente. ¿Desea continuar?',
    "tr": 'Çıktı klasöründe "extracted_subtitles_videofilename" olan klasörler otomatik olarak silinecektir. Devam etmek istiyor musunuz?',
    "zh": '输出文件夹中带有 "extracted_subtitles_videofilename" 的文件夹将自动删除。您要继续吗？',
    "ru": 'Папки с "extracted_subtitles_videofilename" в папке вывода будут автоматически удалены. Хотите продолжить?'
}
BACKUP_SUBTITLES_BEFORE_OVERWRITING_WARNING = {
    "en": "Existing subtitle files will not be backed up before overwriting. Do you want to continue?",
    "es": "Los archivos de subtítulos existentes no se respaldarán antes de sobrescribir. ¿Desea continuar?",
    "tr": "Mevcut altyazı dosyaları üzerine yazılmadan önce yedeklenmeyecektir. Devam etmek istiyor musunuz?",
    "zh": "现有字幕文件在覆盖之前不会备份。您要继续吗？",
    "ru": "Существующие файлы субтитров не будут резервироваться перед перезаписью. Хотите продолжить?"
}
PROMPT_ADDITIONAL_FFSUBSYNC_ARGS = {
    "en": "Enter additional arguments for ffsubsync:",
    "es": "Ingrese argumentos adicionales para ffsubsync:",
    "tr": "ffsubsync için ek argümanlar girin:",
    "zh": "输入 ffsubsync 的附加参数：",
    "ru": "Введите дополнительные аргументы для ffsubsync:"
}
PROMPT_ADDITIONAL_ALASS_ARGS = {
    "en": "Enter additional arguments for alass:",
    "es": "Ingrese argumentos adicionales para alass:",
    "tr": "alass için ek argümanlar girin:",
    "zh": "输入 alass 的附加参数：",
    "ru": "Введите дополнительные аргументы для alass:"
}
LABEL_ADDITIONAL_FFSUBSYNC_ARGS = {
    "en": "Additional arguments for ffsubsync",
    "es": "Argumentos adicionales para ffsubsync",
    "tr": "ffsubsync için ek argümanlar",
    "zh": "ffsubsync 的附加参数",
    "ru": "Дополнительные аргументы для ffsubsync"
}
LABEL_ADDITIONAL_ALASS_ARGS = {
    "en": "Additional arguments for alass",
    "es": "Argumentos adicionales para alass",
    "tr": "alass için ek argümanlar",
    "zh": "alass 的附加参数",
    "ru": "Дополнительные аргументы для alass"
}
LABEL_CHECK_VIDEO_FOR_SUBTITLE_STREAM = {
    "en": "Check video for subtitle streams in alass",
    "es": "Verificar video para flujos de subtítulos en alass",
    "tr": "alass'ta altyazı akışları için videoyu kontrol et",
    "zh": "在 alass 中检查视频的字幕流",
    "ru": "Проверить видео на наличие потоков субтитров в alass"
}
LABEL_BACKUP_SUBTITLES = {
    "en": "Backup subtitles before overwriting",
    "es": "Respaldar subtítulos antes de sobrescribir",
    "tr": "Üzerine yazmadan önce altyazıları yedekle",
    "zh": "覆盖前备份字幕",
    "ru": "Резервное копирование субтитров перед перезаписью"
}
LABEL_KEEP_CONVERTED_SUBTITLES = {
    "en": "Keep converted subtitles",
    "es": "Mantener subtítulos convertidos",
    "tr": "Dönüştürülmüş altyazıları sakla",
    "zh": "保留转换后的字幕",
    "ru": "Сохранить конвертированные субтитры"
}
LABEL_KEEP_EXTRACTED_SUBTITLES = {
    "en": "Keep extracted subtitles",
    "es": "Mantener subtítulos extraídos",
    "tr": "Çıkarılan altyazıları sakla",
    "zh": "保留提取的字幕",
    "ru": "Сохранить извлеченные субтитры"
}
LABEL_REMEMBER_THE_CHANGES = {
    "en": "Remember the changes",
    "es": "Recordar los cambios",
    "tr": "Değişiklikleri hatırla",
    "zh": "记住更改",
    "ru": "Запомнить изменения"
}
LABEL_RESET_TO_DEFAULT_SETTINGS = {
    "en": "Reset to default settings",
    "es": "Restablecer a la configuración predeterminada",
    "tr": "Varsayılan ayarlara sıfırla",
    "zh": "重置为默认设置",
    "ru": "Сбросить настройки по умолчанию"
}
SYNC_TOOL_FFSUBSYNC = {
    "en": "ffsubsync",
    "es": "ffsubsync",
    "tr": "ffsubsync",
    "zh": "ffsubsync",
    "ru": "ffsubsync"
}
SYNC_TOOL_ALASS = {
    "en": "alass",
    "es": "alass",
    "tr": "alass",
    "zh": "alass",
    "ru": "alass"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_NEXT_TO_SUBTITLE = {
    "en": "Save next to subtitle",
    "es": "Guardar junto al subtítulo",
    "tr": "Altyazının yanına kaydet",
    "zh": "保存到字幕旁",
    "ru": "Сохранить рядом с субтитрами"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_NEXT_TO_VIDEO = {
    "en": "Save next to video",
    "es": "Guardar junto al video",
    "tr": "Videonun yanına kaydet",
    "zh": "保存到视频旁",
    "ru": "Сохранить рядом с видео"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME = {
    "en": "Save next to video with same filename",
    "es": "Guardar junto al video con el mismo nombre",
    "tr": "Videonun yanına aynı dosya adıyla kaydet",
    "zh": "与视频的同名文件保存到视频旁",
    "ru": "Сохранить рядом с видео с тем же именем файла"
}
# TEXT SHOULD BE SHORT
OPTION_SAVE_TO_DESKTOP = {
    "en": "Save to Desktop",
    "es": "Guardar en el escritorio",
    "tr": "Masaüstüne kaydet",
    "zh": "保存到桌面",
    "ru": "Сохранить на рабочем столе"
}
# TEXT SHOULD BE SHORT
OPTION_REPLACE_ORIGINAL_SUBTITLE = {
    "en": "Replace original subtitle",
    "es": "Reemplazar subtítulo original",
    "tr": "Orijinal altyazıyı değiştir",
    "zh": "替换原始字幕",
    "ru": "Сохранить на раб. стол"
}
# TEXT SHOULD BE SHORT
OPTION_SELECT_DESTINATION_FOLDER = {
    "en": "Select destination folder",
    "es": "Seleccionar carpeta de destino",
    "tr": "Hedef klasörü seç",
    "zh": "选择目标文件夹",
    "ru": "Выберите папку назначения"
}
CHECKBOX_NO_FIX_FRAMERATE = {
    "en": "Don't fix framerate",
    "es": "No corregir la velocidad de fotogramas",
    "tr": "Kare hızını düzeltme",
    "zh": "不修复帧速率",
    "ru": "Не исправлять частоту кадров"
}
CHECKBOX_GSS = {
    "en": "Use golden-section search",
    "es": "Usar búsqueda de sección áurea",
    "tr": "Altın oran aramasını kullan",
    "zh": "使用黄金分割搜索",
    "ru": "Использовать поиск золотого сечения"
}
CHECKBOX_VAD = {
    "en": "Use auditok instead of WebRTC's VAD",
    "es": "Usar auditok en lugar del VAD de WebRTC",
    "tr": "WebRTC'nin VAD'si yerine auditok kullan",
    "zh": "使用 auditok 而不是 WebRTC 的 VAD",
    "ru": "Использовать auditok вместо VAD WebRTC"
}
# TEXT SHOULD BE SHORT
LABEL_SPLIT_PENALTY = {
    "en": "Split Penalty (Default: 7, Recommended: 5-20, No splits: 0)",
    "es": "Penalización (Predeterminado: 7, Recomendado: 5-20, Sin div: 0)",
    "tr": "Bölme Cezası (Varsayılan: 7, Önerilen: 5-20, Bölme yok: 0)",
    "zh": "分割惩罚（默认：7，推荐：5-20，无分割：0）",
    "ru": "Штраф (По умолчанию: 7, Рекомендуется: 5-20, Без: 0)"
}
PAIR_FILES_TITLE = {
    "en": "Pair Files",
    "es": "Emparejar archivos",
    "tr": "Dosyaları Eşleştir",
    "zh": "配对文件",
    "ru": "Сопоставить файлы"
}
PAIR_FILES_MESSAGE = {
    "en": "The subtitle and video have different filenames. Do you want to pair them?",
    "es": "El subtítulo y el video tienen nombres de archivo diferentes. ¿Quieres emparejarlos?",
    "tr": "Altyazı ve video farklı dosya adlarına sahip. Eşleştirmek istiyor musunuz?",
    "zh": "字幕和视频的文件名不同。您要配对它们吗？",
    "ru": "У субтитров и видео разные имена файлов. Хотите ли вы их сопоставить?"
}
UNPAIRED_SUBTITLES_TITLE = {
    "en": "Unpaired Subtitles",
    "es": "Subtítulos no emparejados",
    "tr": "Eşleşmemiş Altyazılar",
    "zh": "未配对的字幕",
    "ru": "Несопоставленные субтитры"
}
UNPAIRED_SUBTITLES_MESSAGE = {
    "en": "There are {unpaired_count} unpaired subtitle(s). Do you want to add them as subtitles with [no video] tag?",
    "es": "Hay {unpaired_count} subtítulo(s) no emparejado(s). ¿Quieres agregarlos como subtítulos con la etiqueta [sin video]?",
    "tr": "{unpaired_count} eşleşmemiş altyazı var. Bunları [video yok] etiketiyle altyazı olarak eklemek istiyor musunuz?",
    "zh": "有 {unpaired_count} 个未配对的字幕。您要将它们添加为带有 [no video] 标签的字幕吗？",
    "ru": "Есть {unpaired_count} несопоставленный(ые) субтитр(ы). Хотите добавить их как субтитры с тегом [нет видео]?"
}
NO_VIDEO = {
    "en": "[no video]",
    "es": "[sin video]",
    "tr": "[video yok]",
    "zh": "[没有视频]",
    "ru": "[нет видео]"
}
NO_SUBTITLE = {
    "en": "[no subtitle]",
    "es": "[sin subtítulo]",
    "tr": "[altyazı yok]",
    "zh": "[没有字幕]",
    "ru": "[нет субтитров]"
}
VIDEO_OR_SUBTITLE_TEXT = {
    "en": "Video or subtitle",
    "es": "Video o subtítulo",
    "tr": "Video veya altyazı",
    "zh": "视频或字幕",
    "ru": "Видео или субтитры"
}
VIDEO_INPUT_LABEL = {
    "en": "Video/Reference subtitle",
    "es": "Video/Subtítulo de referencia",
    "tr": "Video/Referans altyazı",
    "zh": "视频/参考字幕",
    "ru": "Видео/Справочные субтитры"
}
SUBTITLE_INPUT_LABEL = {
    "en": "Subtitle",
    "es": "Subtítulo",
    "tr": "Altyazı",
    "zh": "字幕",
    "ru": "Субтитры"
}
SUBTITLE_FILES_TEXT = {
    "en": "Subtitle files",
    "es": "Archivos de subtítulos",
    "tr": "Altyazı dosyaları",
    "zh": "字幕文件",
    "ru": "Файлы субтитров"
}
CONTEXT_MENU_REMOVE = {
    "en": "Remove",
    "es": "Eliminar",
    "tr": "Kaldır",
    "zh": "删除",
    "ru": "Удалить"
}
CONTEXT_MENU_CHANGE = {
    "en": "Change",
    "es": "Cambiar",
    "tr": "Değiştir",
    "zh": "更改",
    "ru": "Изменить"
}
CONTEXT_MENU_ADD_PAIR = {
    "en": "Add Pair",
    "es": "Agregar par",
    "tr": "Çift Ekle",
    "zh": "添加配对",
    "ru": "Добавить пару"
}
CONTEXT_MENU_CLEAR_ALL = {
    "en": "Clear All",
    "es": "Limpiar todo",
    "tr": "Hepsini Temizle",
    "zh": "清除所有",
    "ru": "Очистить все"
}
CONTEXT_MENU_SHOW_PATH = {
    "en": "Show path",
    "es": "Mostrar ruta",
    "tr": "Yolu göster",
    "zh": "显示路径",
    "ru": "Показать путь"
}
BUTTON_ADD_FILES = {
    "en": "Add files",
    "es": "Agregar archivos",
    "tr": "Dosya ekle",
    "zh": "添加文件",
    "ru": "Добавить файлы"
}
MENU_ADD_FOLDER = {
    "en": "Add Folder",
    "es": "Agregar carpeta",
    "tr": "Klasör ekle",
    "zh": "添加文件夹",
    "ru": "Добавить папку"
}
MENU_ADD_MULTIPLE_FILES = {
    "en": "Add Multiple Files",
    "es": "Agregar múltiples archivos",
    "tr": "Çoklu Dosya Ekle",
    "zh": "添加多个文件",
    "ru": "Добавить несколько файлов"
}
MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS = {
    "en": "Add Reference Subtitle/Subtitle Pairs",
    "es": "Agregar pares de subtítulos de referencia/subtítulos",
    "tr": "Referans Altyazı/Altyazı Çiftleri Ekle",
    "zh": "添加参考字幕/字幕对",
    "ru": "Добавить пары субтитров/субтитров справки"
}
ALASS_SPEED_OPTIMIZATION_TEXT = {
    "en": "Disable speed optimization",
    "es": "Deshabilitar optimización de velocidad",
    "tr": "Hız optimizasyonunu devre dışı bırak",
    "zh": "禁用速度优化",
    "ru": "Отключить оптимизацию скорости"
}
ALASS_DISABLE_FPS_GUESSING_TEXT = {
    "en": "Disable FPS guessing",
    "es": "Deshabilitar adivinación de FPS",
    "tr": "FPS tahminini devre dışı bırak",
    "zh": "禁用 FPS 猜测",
    "ru": "Отключить догадку FPS"
}
REF_DROP_TEXT = {
    "en": "Drag and drop reference subtitles here\nor click to browse.",
    "es": "Arrastre y suelte subtítulos de referencia aquí\no haga clic para buscar.",
    "tr": "Referans altyazıları buraya sürükleyip bırakın\nveya göz atmak için tıklayın.",
    "zh": "将参考字幕拖放到此处\n或点击浏览。",
    "ru": "Перетащите сюда справочные субтитры\nили нажмите, чтобы выбрать."
}
SUB_DROP_TEXT = {
    "en": "Drag and drop subtitles here\nor click to browse.",
    "es": "Arrastre y suelte subtítulos aquí\no haga clic para buscar.",
    "tr": "Altyazıları buraya sürükleyip bırakın\nveya göz atmak için tıklayın.",
    "zh": "将字幕拖放到此处\n或点击浏览。",
    "ru": "Перетащите сюда субтитры\nили нажмите, чтобы выбрать."
}
REF_LABEL_TEXT = {
    "en": "Reference Subtitles",
    "es": "Subtítulos de referencia",
    "tr": "Referans Altyazılar",
    "zh": "参考字幕",
    "ru": "Справочные субтитры"
}
SUB_LABEL_TEXT = {
    "en": "Subtitles",
    "es": "Subtítulos",
    "tr": "Altyazılar",
    "zh": "字幕",
    "ru": "Субтитры"
}
PROCESS_PAIRS = {
    "en": "Add Pairs",
    "es": "Agregar pares",
    "tr": "Çiftleri Ekle",
    "zh": "添加配对",
    "ru": "Добавить пары"
}
# TEXT SHOULD BE SHORT
SYNC_TOOL_LABEL_TEXT = {
    "en": "Sync using",
    "es": "Sincr. con",
    "tr": "Senkr. aracı",
    "zh": "使用同步工具",
    "ru": "Синхр. с"
}
EXPLANATION_TEXT_IN_REFERENCE__SUBTITLE_PARIRING = {
    "en": """How the Pairing Works?
    """+PROGRAM_NAME+""" will automatically match reference subtitles and subtitle files with similar names. 
    For example: "S01E01.srt" will be paired with "1x01.srt"
    Supported combinations: S01E01, S1E1, S01E1, S1E01, 1x01, 01x1, 01x01, 1x1""",
    "es": """¿Cómo funciona el emparejamiento?
    """+PROGRAM_NAME+""" emparejará automáticamente los subtítulos de referencia y los archivos de subtítulos con nombres similares. 
    Por ejemplo: "S01E01.srt" se emparejará con "1x01.srt"
    Combinaciones compatibles: S01E01, S1E1, S01E1, S1E01, 1x01, 01x1, 01x01, 1x1""",
    "tr": """Eşleştirme Nasıl Çalışır?
    """+PROGRAM_NAME+""" benzer isimlere sahip referans altyazıları ve altyazı dosyalarını otomatik olarak eşleştirecektir. 
    Örneğin: "S01E01.srt" "1x01.srt" ile eşleştirilecektir
    Desteklenen kombinasyonlar: S01E01, S1E1, S01E1, S1E01, 1x01, 01x1, 01x01, 1x1""",
    "zh": """配对如何工作？
    """+PROGRAM_NAME+""" 将自动匹配具有相似名称的参考字幕和字幕文件。
    例如："S01E01.srt" 将与 "1x01.srt" 配对
    支持的组合：S01E01, S1E1, S01E1, S1E01, 1x01, 01x1, 01x01, 1x1""",
    "ru": """Как работает сопоставление?
    """+PROGRAM_NAME+""" автоматически сопоставит эталонные субтитры и файлы субтитров с похожими именами.
    Например: "S01E01.srt" будет сопоставлен с "1x01.srt"
    Поддерживаемые комбинации: S01E01, S1E1, S01E1, S1E01, 1x01, 01x1, 01x01, 1x1"""
}
SUCCESS_LOG_TEXT = {
    "en": "Success! Subtitle shifted by {milliseconds} milliseconds and saved to: {new_subtitle_file}",
    "es": "¡Éxito! Subtítulo desplazado por {milliseconds} milisegundos y guardado en: {new_subtitle_file}",
    "tr": "Başarılı! Altyazı {milliseconds} milisaniye kaydırıldı ve kaydedildi: {new_subtitle_file}",
    "zh": "成功！字幕移位 {milliseconds} 毫秒，并保存到：{new_subtitle_file}",
    "ru": "Успех! Субтитры сдвинуты на {milliseconds} миллисекунд и сохранены в: {new_subtitle_file}"
}
SYNC_SUCCESS_MESSAGE = {
    "en": "Success! Synchronized subtitle saved to: {output_subtitle_file}",
    "es": "¡Éxito! Subtítulo sincronizado guardado en: {output_subtitle_file}",
    "tr": "Başarılı! Senkronize edilmiş altyazı kaydedildi: {output_subtitle_file}",
    "zh": "成功！同步字幕保存到：{output_subtitle_file}",
    "ru": "Успех! Синхронизированные субтитры сохранены в: {output_subtitle_file}"
}
ERROR_SAVING_SUBTITLE = {
    "en": "Error saving subtitle file: {error_message}",
    "es": "Error al guardar el archivo de subtítulos: {error_message}",
    "tr": "Altyazı dosyası kaydedilirken hata: {error_message}",
    "zh": "保存字幕文件时出错：{error_message}",
    "ru": "Ошибка сохранения файла субтитров: {error_message}"
}
NON_ZERO_MILLISECONDS = {
    "en": "Please enter a non-zero value for milliseconds.",
    "es": "Por favor, ingrese un valor distinto de cero para milisegundos.",
    "tr": "Lütfen milisaniye için sıfır olmayan bir değer girin.",
    "zh": "请输入非零毫秒值。",
    "ru": "Пожалуйста, введите ненулевое значение для миллисекунд."
}
SELECT_ONLY_ONE_OPTION = {
    "en": "Please select only one option: Save to Desktop or Replace Original Subtitle.",
    "es": "Por favor, seleccione solo una opción: Guardar en el escritorio o Reemplazar el subtítulo original.",
    "tr": "Lütfen yalnızca bir seçenek seçin: Masaüstüne Kaydet veya Orijinal Altyazıyı Değiştir.",
    "zh": "请只选择一个选项：保存到桌面或替换原始字幕。",
    "ru": "Пожалуйста, выберите только один вариант: Сохранить на рабочем столе или Заменить оригинальный субтитр."
}
VALID_NUMBER_MILLISECONDS = {
    "en": "Please enter a valid number of milliseconds.",
    "es": "Por favor, ingrese un número válido de milisegundos.",
    "tr": "Lütfen geçerli bir milisaniye sayısı girin.",
    "zh": "请输入有效的毫秒数。",
    "ru": "Пожалуйста, введите допустимое количество миллисекунд."
}
SELECT_SUBTITLE = {
    "en": "Please select a subtitle file.",
    "es": "Por favor, seleccione un archivo de subtítulos.",
    "tr": "Lütfen bir altyazı dosyası seçin.",
    "zh": "请选择一个字幕文件。",
    "ru": "Пожалуйста, выберите файл субтитров."
}
SELECT_VIDEO = {
    "en": "Please select a video file.",
    "es": "Por favor, seleccione un archivo de video.",
    "tr": "Lütfen bir video dosyası seçin.",
    "zh": "请选择一个视频文件。",
    "ru": "Пожалуйста, выберите файл видео."
}
SELECT_VIDEO_OR_SUBTITLE = {
    "en": "Please select a video or reference subtitle.",
    "es": "Por favor, seleccione un video o subtítulo de referencia.",
    "tr": "Lütfen bir video veya referans altyazı seçin.",
    "zh": "请选择一个视频或参考字幕。",
    "ru": "Пожалуйста, выберите видео или справочные субтитры."
}
DROP_VIDEO_SUBTITLE_PAIR = {
    "en": "Please drop a video, subtitle or pair.",
    "es": "Por favor, suelte un video, subtítulo o par.",
    "tr": "Lütfen bir video, altyazı veya çift bırakın.",
    "zh": "请拖放一个视频、字幕或配对。",
    "ru": "Пожалуйста, перетащите видео, субтитры или пару."
}
DROP_VIDEO_OR_SUBTITLE = {
    "en": "Please drop a video or reference subtitle file.",
    "es": "Por favor, suelte un archivo de video o subtítulo de referencia.",
    "tr": "Lütfen bir video veya referans altyazı dosyası bırakın.",
    "zh": "请拖放一个视频或参考字幕文件。",
    "ru": "Пожалуйста, перетащите видео или файл справочных субтитров."
}
DROP_SUBTITLE_FILE = {
    "en": "Please drop a subtitle file.",
    "es": "Por favor, suelte un archivo de subtítulos.",
    "tr": "Lütfen bir altyazı dosyası bırakın.",
    "zh": "请拖放一个字幕文件。",
    "ru": "Пожалуйста, перетащите файл субтитров."
}
DROP_SINGLE_SUBTITLE_FILE = {
    "en": "Please drop a single subtitle file.",
    "es": "Por favor, suelte un solo archivo de subtítulos.",
    "tr": "Lütfen tek bir altyazı dosyası bırakın.",
    "zh": "请拖放一个单独的字幕文件。",
    "ru": "Пожалуйста, перетащите один файл субтитров."
}
DROP_SINGLE_SUBTITLE_PAIR = {
    "en": "Please drop a single subtitle or pair.",
    "es": "Por favor, suelte un solo subtítulo o par.",
    "tr": "Lütfen tek bir altyazı veya çift bırakın.",
    "zh": "请拖放一个单独的字幕或配对。",
    "ru": "Пожалуйста, перетащите один субтитр или пару."
}
SELECT_BOTH_FILES = {
    "en": "Please select both video/reference subtitle and subtitle file.",
    "es": "Por favor, seleccione tanto el archivo de video/subtítulo de referencia como el archivo de subtítulos.",
    "tr": "Lütfen hem video/referans altyazı hem de altyazı dosyasını seçin.",
    "zh": "请选择视频/参考字幕和字幕文件。",
    "ru": "Пожалуйста, выберите как видео/справочный субтитр, так и файл субтитров."
}
SELECT_DIFFERENT_FILES = {
    "en": "Please select different subtitle files.",
    "es": "Por favor, seleccione diferentes archivos de subtítulos.",
    "tr": "Lütfen farklı altyazı dosyaları seçin.",
    "zh": "请选择不同的字幕文件。",
    "ru": "Пожалуйста, выберите разные файлы субтитров."
}
SUBTITLE_FILE_NOT_EXIST = {
    "en": "Subtitle file does not exist.",
    "es": "El archivo de subtítulos no existe.",
    "tr": "Altyazı dosyası mevcut değil.",
    "zh": "字幕文件不存在。",
    "ru": "Файл субтитров не существует."
}
VIDEO_FILE_NOT_EXIST = {
    "en": "Video file does not exist.",
    "es": "El archivo de video no existe.",
    "tr": "Video dosyası mevcut değil.",
    "zh": "视频文件不存在。",
    "ru": "Файл видео не существует."
}
ERROR_LOADING_SUBTITLE = {
    "en": "Error loading subtitle file: {error_message}",
    "es": "Error al cargar el archivo de subtítulos: {error_message}",
    "tr": "Altyazı dosyası yüklenirken hata: {error_message}",
    "zh": "加载字幕文件时出错：{error_message}",
    "ru": "Ошибка загрузки файла субтитров: {error_message}"
}
ERROR_CONVERT_TIMESTAMP = {
    "en": "Failed to convert timestamp '{timestamp}' for format '{format_type}'",
    "es": "Error al convertir la marca de tiempo '{timestamp}' para el formato '{format_type}'",
    "tr": "'{timestamp}' zaman damgası '{format_type}' formatına dönüştürülemedi",
    "zh": "无法将时间戳 '{timestamp}' 转换为格式 '{format_type}'",
    "ru": "Не удалось преобразовать метку времени '{timestamp}' в формат '{format_type}'"
}
ERROR_PARSING_TIME_STRING = {
    "en": "Error parsing time string '{time_str}'",
    "es": "Error al analizar la cadena de tiempo '{time_str}'",
    "tr": "'{time_str}' zaman dizesi ayrıştırılırken hata",
    "zh": "解析时间字符串 '{time_str}' 时出错",
    "ru": "Ошибка разбора временной строки '{time_str}'"
}
ERROR_PARSING_TIME_STRING_DETAILED = {
    "en": "Error parsing time string '{time_str}' for format '{format_type}': {error_message}",
    "es": "Error al analizar la cadena de tiempo '{time_str}' para el formato '{format_type}': {error_message}",
    "tr": "'{time_str}' zaman dizesi '{format_type}' formatı için ayrıştırılırken hata: {error_message}",
    "zh": "解析时间字符串 '{time_str}' 为格式 '{format_type}' 时出错：{error_message}",
    "ru": "Ошибка разбора временной строки '{time_str}' для формата '{format_type}': {error_message}"
}
NO_FILES_TO_SYNC = {
    "en": "No files to sync. Please add files to the batch list.",
    "es": "No hay archivos para sincronizar. Por favor, agregue archivos a la lista de lotes.",
    "tr": "Senkronize edilecek dosya yok. Lütfen toplu listeye dosya ekleyin.",
    "zh": "没有要同步的文件。请将文件添加到批处理列表。",
    "ru": "Нет файлов для синхронизации. Пожалуйста, добавьте файлы в список пакетов."
}
NO_VALID_FILE_PAIRS = {
    "en": "No valid file pairs to sync.",
    "es": "No hay pares de archivos válidos para sincronizar.",
    "tr": "Senkronize edilecek geçerli dosya çifti yok.",
    "zh": "没有有效的文件对要同步。",
    "ru": "Нет действительных пар файлов для синхронизации."
}
ERROR_PROCESS_TERMINATION = {
    "en": "Error occurred during process termination: {error_message}",
    "es": "Ocurrió un error durante la terminación del proceso: {error_message}",
    "tr": "İşlem sonlandırma sırasında hata oluştu: {error_message}",
    "zh": "在进程终止期间发生错误：{error_message}",
    "ru": "Произошла ошибка во время завершения процесса: {error_message}"
}
AUTO_SYNC_CANCELLED = {
    "en": "Automatic synchronization cancelled.",
    "es": "Sincronización automática cancelada.",
    "tr": "Otomatik senkronizasyon iptal edildi.",
    "zh": "自动同步已取消。",
    "ru": "Автоматическая синхронизация отменена."
}
BATCH_SYNC_CANCELLED = {
    "en": "Batch synchronization cancelled.",
    "es": "Sincronización por lotes cancelada.",
    "tr": "Toplu senkronizasyon iptal edildi.",
    "zh": "批量同步已取消。",
    "ru": "Пакетная синхронизация отменена."
}
NO_SYNC_PROCESS = {
    "en": "No synchronization process to cancel.",
    "es": "No hay proceso de sincronización para cancelar.",
    "tr": "İptal edilecek senkronizasyon işlemi yok.",
    "zh": "没有要取消的同步进程。",
    "ru": "Нет процесса синхронизации для отмены."
}
INVALID_SYNC_TOOL = {
    "en": "Invalid sync tool selected.",
    "es": "Herramienta de sincronización inválida seleccionada.",
    "tr": "Geçersiz senkronizasyon aracı seçildi.",
    "zh": "选择了无效的同步工具。",
    "ru": "Выбран недопустимый инструмент синхронизации."
}
FAILED_START_PROCESS = {
    "en": "Failed to start process: {error_message}",
    "es": "Error al iniciar el proceso: {error_message}",
    "tr": "İşlem başlatılamadı: {error_message}",
    "zh": "无法启动进程：{error_message}",
    "ru": "Не удалось запустить процесс: {error_message}"
}
ERROR_OCCURRED = {
    "en": "Error occurred: {error_message}",
    "es": "Ocurrió un error: {error_message}",
    "tr": "Hata oluştu: {error_message}",
    "zh": "发生错误：{error_message}",
    "ru": "Произошла ошибка: {error_message}"
}
ERROR_EXECUTING_COMMAND = {
    "en": "Error executing command: ",
    "es": "Error al ejecutar el comando: ",
    "tr": "Komut yürütülürken hata: ",
    "zh": "执行命令时出错：",
    "ru": "Ошибка выполнения команды: "
}
DROP_VALID_FILES = {
    "en": "Please drop valid subtitle and video files.",
    "es": "Por favor, suelte archivos de subtítulos y video válidos.",
    "tr": "Lütfen geçerli altyazı ve video dosyalarını bırakın.",
    "zh": "请拖放有效的字幕和视频文件。",
    "ru": "Пожалуйста, перетащите действительные файлы субтитров и видео."
}
PAIRS_ADDED = {
    "en": "Added {count} pair(s)",
    "es": "Agregado {count} par(es)",
    "tr": "{count} çift eklendi",
    "zh": "添加了 {count} 对",
    "ru": "Добавлено {count} пар(ы)"
}
UNPAIRED_FILES_ADDED = {
    "en": "Added {count} unpaired file(s)",
    "es": "Agregado {count} archivo(s) no emparejado(s)",
    "tr": "{count} eşleşmemiş dosya eklendi",
    "zh": "添加了 {count} 个未配对文件",
    "ru": "Добавлено {count} несопоставленный файл(ы)"
}
UNPAIRED_FILES = {
    "en": "{count} unpaired file(s)",
    "es": "{count} archivo(s) no emparejado(s)",
    "tr": "{count} eşleşmemiş dosya",
    "zh": "{count} 个未配对文件",
    "ru": "{count} несопоставленный файл(ы)"
}
DUPLICATE_PAIRS_SKIPPED = {
    "en": "{count} duplicate pair(s) skipped",
    "es": "{count} par(es) duplicado(s) omitido(s)",
    "tr": "{count} yinelenen çift atlandı",
    "zh": "跳过 {count} 个重复对",
    "ru": "{count} дублированный пар(а) пропущен(о)"
}
PAIR_ALREADY_EXISTS = {
    "en": "This pair already exists.",
    "es": "Este par ya existe.",
    "tr": "Bu çift zaten mevcut.",
    "zh": "此对已存在。",
    "ru": "Эта пара уже существует."
}
PAIR_ADDED = {
    "en": "Added 1 pair.",
    "es": "Agregado 1 par.",
    "tr": "1 çift eklendi.",
    "zh": "添加了 1 对。",
    "ru": "Добавлена 1 пара."
}
SAME_FILE_ERROR = {
    "en": "Cannot use the same file for both inputs.",
    "es": "No se puede usar el mismo archivo para ambas entradas.",
    "tr": "Her iki giriş için de aynı dosya kullanılamaz.",
    "zh": "无法同时使用同一文件作为两个输入。",
    "ru": "Нельзя использовать один и тот же файл для обоих входов."
}
PAIR_ALREADY_EXISTS = {
    "en": "This pair already exists. Please select a different file.",
    "es": "Este par ya existe. Por favor, seleccione un archivo diferente.",
    "tr": "Bu çift zaten mevcut. Lütfen farklı bir dosya seçin.",
    "zh": "此对已存在。请选择其他文件。",
    "ru": "Эта пара уже существует. Пожалуйста, выберите другой файл."
}
SUBTITLE_ADDED = {
    "en": "Subtitle added.",
    "es": "Subtítulo agregado.",
    "tr": "Altyazı eklendi.",
    "zh": "字幕已添加。",
    "ru": "Субтитры добавлены."
}
VIDEO_ADDED = {
    "en": "Video/reference subtitle added.",
    "es": "Video/subtítulo de referencia agregado.",
    "tr": "Video/referans altyazı eklendi.",
    "zh": "视频/参考字幕已添加。",
    "ru": "Видео/справочный субтитр добавлен."
}
FILE_CHANGED = {
    "en": "File changed.",
    "es": "Archivo cambiado.",
    "tr": "Dosya değiştirildi.",
    "zh": "文件已更改。",
    "ru": "Файл изменен."
}
SELECT_ITEM_TO_CHANGE = {
    "en": "Please select an item to change.",
    "es": "Por favor, seleccione un elemento para cambiar.",
    "tr": "Lütfen değiştirmek için bir öğe seçin.",
    "zh": "请选择要更改的项目。",
    "ru": "Пожалуйста, выберите элемент для изменения."
}
SELECT_ITEM_TO_REMOVE = {
    "en": "Please select an item to remove.",
    "es": "Por favor, seleccione un elemento para eliminar.",
    "tr": "Lütfen kaldırmak için bir öğe seçin.",
    "zh": "请选择要删除的项目。",
    "ru": "Пожалуйста, выберите элемент для удаления."
}
FILE_NOT_EXIST = {
    "en": "File specified in the argument does not exist.",
    "es": "El archivo especificado en el argumento no existe.",
    "tr": "Argümanda belirtilen dosya mevcut değil.",
    "zh": "参数中指定的文件不存在。",
    "ru": "Файл, указанный в аргументе, не существует."
}
MULTIPLE_ARGUMENTS = {
    "en": "Multiple arguments provided. Please provide only one subtitle file path.",
    "es": "Se proporcionaron múltiples argumentos. Por favor, proporcione solo una ruta de archivo de subtítulos.",
    "tr": "Birden fazla argüman sağlandı. Lütfen yalnızca bir altyazı dosyası yolu sağlayın.",
    "zh": "提供了多个参数。请只提供一个字幕文件路径。",
    "ru": "Предоставлено несколько аргументов. Пожалуйста, укажите только один путь к файлу субтитров."
}
INVALID_FILE_FORMAT = {
    "en": "Invalid file format. Please provide a subtitle file.",
    "es": "Formato de archivo inválido. Por favor, proporcione un archivo de subtítulos.",
    "tr": "Geçersiz dosya formatı. Lütfen bir altyazı dosyası sağlayın.",
    "zh": "无效的文件格式。请提供一个字幕文件。",
    "ru": "Недопустимый формат файла. Пожалуйста, укажите файл субтитров."
}
INVALID_SYNC_TOOL_SELECTED = {
    "en": "Invalid sync tool selected.",
    "es": "Herramienta de sincronización inválida seleccionada.",
    "tr": "Geçersiz senkronizasyon aracı seçildi.",
    "zh": "选择了无效的同步工具。",
    "ru": "Выбран недопустимый инструмент синхронизации."
}
TEXT_SELECTED_FOLDER = {
    "en": "Selected folder: {}",
    "es": "Carpeta seleccionada: {}",
    "tr": "Seçilen klasör: {}",
    "zh": "已选择文件夹：{}",
    "ru": "Выбранная папка: {}"
}
TEXT_NO_FOLDER_SELECTED = {
    "en": "No folder selected.",
    "es": "No se seleccionó ninguna carpeta.",
    "tr": "Klasör seçilmedi.",
    "zh": "未选择文件夹。",
    "ru": "Папка не выбрана."
}
TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST = {
    "en": "The selected destination folder does not exist.",
    "es": "La carpeta de destino seleccionada no existe.",
    "tr": "Seçilen hedef klasör mevcut değil.",
    "zh": "所选的目标文件夹不存在。",
    "ru": "Выбранная папка назначения не существует."
}
ADDED_PAIRS_MSG = {
    "en": "Added {} reference subtitle pair{}",
    "es": "Agregado {} par{} de subtítulos de referencia",
    "tr": "{} referans altyazı çifti eklendi",
    "zh": "添加了 {} 个参考字幕对",
    "ru": "Добавлено {} пар{а} справочных субтитров"
}
SKIPPED_DUPLICATES_MSG = {
    "en": "Skipped {} duplicate pair{}",
    "es": "Omitido {} par{} duplicado{}",
    "tr": "{} yinelenen çift atlandı",
    "zh": "跳过 {} 个重复对",
    "ru": "Пропущено {} дублированный пар{а}"
}
INVALID_PARENT_ITEM = {
    "en": "Invalid parent item with no values.",
    "es": "Elemento principal inválido sin valores.",
    "tr": "Değer içermeyen geçersiz üst öğe.",
    "zh": "无值的无效父项目。",
    "ru": "Недопустимый родительский элемент без значений."
}
SKIP_NO_VIDEO_NO_SUBTITLE = {
    "en": "Skipping entry with no video and no subtitle.",
    "es": "Omitiendo entrada sin video ni subtítulo.",
    "tr": "Video ve altyazı olmayan girdi atlanıyor.",
    "zh": "跳过没有视频和没有字幕的条目。",
    "ru": "Пропуск записи без видео и субтитров."
}
SKIP_NO_SUBTITLE = {
    "en": "Skipping '{video_file}': No subtitle file.",
    "es": "Omitiendo '{video_file}': No hay archivo de subtítulos.",
    "tr": "'{video_file}' atlanıyor: Altyazı dosyası yok.",
    "zh": "跳过 '{video_file}'：没有字幕文件。",
    "ru": "Пропуск '{video_file}': Нет файла субтитров."
}
SKIP_NO_VIDEO = {
    "en": "Skipping '{subtitle_file}': No video/reference file.",
    "es": "Omitiendo '{subtitle_file}': No hay archivo de video/referencia.",
    "tr": "'{subtitle_file}' atlanıyor: Video/referans dosyası yok.",
    "zh": "跳过 '{subtitle_file}'：没有视频/参考文件。",
    "ru": "Пропуск '{subtitle_file}': Нет видео/справочного файла."
}
SKIP_UNPAIRED_ITEM = {
    "en": "Unpaired item skipped.",
    "es": "Elemento no emparejado omitido.",
    "tr": "Eşleşmemiş öğe atlandı.",
    "zh": "跳过未配对的项目。",
    "ru": "Пропущен несопоставленный элемент."
}
SKIPPING_ALREADY_SYNCED = {
    "en": "Skipping {filename}: Already synced.",
    "es": "Omitiendo {filename}: Ya sincronizado.",
    "tr": "{filename} atlanıyor: Zaten senkronize.",
    "zh": "跳过 {filename}：已同步。",
    "ru": "Пропуск {filename}: Уже синхронизирован."
}
CONVERTING_SUBTITLE = {
    "en": "Converting {file_extension} to SRT...",
    "es": "Convirtiendo {file_extension} a SRT...",
    "tr": "{file_extension} uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 {file_extension} 转换为 SRT...",
    "ru": "Преобразование {file_extension} в SRT..."
}
SYNCING_LOG_TEXT = {
    "en": "[{}/{}] Syncing {} with {}...\n",
    "es": "[{}/{}] Sincronizando {} con {}...\n",
    "tr": "[{}/{}] {} ile {} senkronize ediliyor...\n",
    "zh": "[{}/{}] 正在同步 {} 和 {}...\n",
    "ru": "[{}/{}] Синхронизация {} с {}...\n"
}
ERROR_CONVERTING_SUBTITLE = {
    "en": "Error converting subtitle: {error_message}",
    "es": "Error al convertir subtítulo: {error_message}",
    "tr": "Altyazı dönüştürme hatası: {error_message}",
    "zh": "转换字幕时出错：{error_message}",
    "ru": "Ошибка преобразования субтитров: {error_message}"
}
SUBTITLE_CONVERTED = {
    "en": "Subtitle successfully converted and saved to: {srt_file}.",
    "es": "Subtítulo convertido exitosamente y guardado en: {srt_file}.",
    "tr": "Altyazı başarıyla dönüştürüldü ve kaydedildi: {srt_file}.",
    "zh": "字幕成功转换并保存到：{srt_file}。",
    "ru": "Субтитры успешно преобразованы и сохранены в: {srt_file}."
}
ERROR_UNSUPPORTED_CONVERSION = {
    "en": "Error: Conversion for {file_extension} is not supported.",
    "es": "Error: La conversión para {file_extension} no está soportada.",
    "tr": "Hata: {file_extension} dönüştürme desteklenmiyor.",
    "zh": "错误：不支持 {file_extension} 的转换。",
    "ru": "Ошибка: Конвертация для {file_extension} не поддерживается."
}
FAILED_CONVERT_SUBTITLE = {
    "en": "Failed to convert subtitle file: {subtitle_file}",
    "es": "Error al convertir el archivo de subtítulos: {subtitle_file}",
    "tr": "Altyazı dosyası dönüştürülemedi: {subtitle_file}",
    "zh": "无法转换字幕文件：{subtitle_file}",
    "ru": "Не удалось преобразовать файл субтитров: {subtitle_file}"
}
FAILED_CONVERT_VIDEO = {
    "en": "Failed to convert video/reference file: {video_file}",
    "es": "Error al convertir archivo de video/referencia: {video_file}",
    "tr": "Video/referans dosyası dönüştürülemedi: {video_file}",
    "zh": "无法转换视频/参考文件：{video_file}",
    "ru": "Не удалось преобразовать видео/справочный файл: {video_file}"
}
SPLIT_PENALTY_ZERO = {
    "en": "Split penalty is set to 0. Using --no-split argument...",
    "es": "La penalización de división se establece en 0. Usando el argumento --no-split...",
    "tr": "Bölme cezası 0 olarak ayarlandı. --no-split argümanı kullanılıyor...",
    "zh": "分割惩罚设置为 0。使用 --no-split 参数...",
    "ru": "Штраф за разделение установлен на 0. Используется аргумент --no-split..."
}
SPLIT_PENALTY_SET = {
    "en": "Split penalty is set to {split_penalty}...",
    "es": "La penalización de división se establece en {split_penalty}...",
    "tr": "Bölme cezası {split_penalty} olarak ayarlandı...",
    "zh": "分割惩罚设置为 {split_penalty}...",
    "ru": "Штраф за разделение установлен на {split_penalty}..."
}
USING_REFERENCE_SUBTITLE = {
    "en": "Using reference subtitle for syncing...",
    "es": "Usando subtítulo de referencia para sincronizar...",
    "tr": "Senkronizasyon için referans altyazı kullanılıyor...",
    "zh": "使用参考字幕进行同步...",
    "ru": "Использование справочных субтитров для синхронизации..."
}
USING_VIDEO_FOR_SYNC = {
    "en": "Using video for syncing...",
    "es": "Usando video para sincronizar...",
    "tr": "Senkronizasyon için video kullanılıyor...",
    "zh": "使用视频进行同步...",
    "ru": "Использование видео для синхронизации..."
}
ENABLED_NO_FIX_FRAMERATE = {
    "en": "Enabled: Don't fix framerate.",
    "es": "Habilitado: No corregir la velocidad de fotogramas.",
    "tr": "Etkinleştirildi: Kare hızını düzeltme.",
    "zh": "已启用：不修复帧速率。",
    "ru": "Включено: Не исправлять частоту кадров."
}
ENABLED_GSS = {
    "en": "Enabled: Golden-section search.",
    "es": "Habilitado: Búsqueda de sección áurea.",
    "tr": "Etkinleştirildi: Altın oran araması.",
    "zh": "已启用：黄金分割搜索。",
    "ru": "Включено: Поиск золотого сечения."
}
ENABLED_AUDITOK_VAD = {
    "en": "Enabled: Using auditok instead of WebRTC's VAD.",
    "es": "Habilitado: Usando auditok en lugar de VAD de WebRTC.",
    "tr": "Etkinleştirildi: WebRTC'nin VAD'si yerine auditok kullanılıyor.",
    "zh": "已启用：使用 auditok 而不是 WebRTC 的 VAD。",
    "ru": "Включено: Использование auditok вместо VAD WebRTC."
}
ADDITIONAL_ARGS_ADDED = {
    "en": "Additional arguments: {additional_args}",
    "es": "Argumentos adicionales: {additional_args}",
    "tr": "Ek argümanlar: {additional_args}",
    "zh": "附加参数：{additional_args}",
    "ru": "Дополнительные аргументы: {additional_args}"
}
SYNCING_STARTED = {
    "en": "Syncing started:",
    "es": "Sincronización iniciada:",
    "tr": "Senkronizasyon başlatıldı:",
    "zh": "开始同步：",
    "ru": "Синхронизация начата:"
}
SYNCING_ENDED = {
    "en": "Syncing ended.",
    "es": "Sincronización finalizada.",
    "tr": "Senkronizasyon tamamlandı.",
    "zh": "同步结束。",
    "ru": "Синхронизация завершена."
}
SYNC_SUCCESS = {
    "en": "Success! Synchronized subtitle saved to: {output_subtitle_file}\n\n",
    "es": "¡Éxito! Subtítulo sincronizado guardado en: {output_subtitle_file}\n\n",
    "tr": "Başarılı! Senkronize altyazı kaydedildi: {output_subtitle_file}\n\n",
    "zh": "成功！同步字幕保存到：{output_subtitle_file}\n\n,",
    "ru": "Успех! Синхронизированные субтитры сохранены в: {output_subtitle_file}\n\n"
}
SYNC_ERROR = {
    "en": "Error occurred during synchronization of {filename}",
    "es": "Ocurrió un error durante la sincronización de {filename}",
    "tr": "{filename} senkronizasyonu sırasında hata oluştu",
    "zh": "同步 {filename} 时出错",
    "ru": "Произошла ошибка во время синхронизации {filename}"
}
SYNC_ERROR_OCCURRED = {
    "en": "Error occurred during synchronization. Please check the log messages.",
    "es": "Ocurrió un error durante la sincronización. Por favor, revise los mensajes de registro.",
    "tr": "Senkronizasyon sırasında hata oluştu. Lütfen kayıt mesajlarını kontrol edin.",
    "zh": "同步期间发生错误。请检查日志消息。",
    "ru": "Произошла ошибка во время синхронизации. Пожалуйста, проверьте сообщения журнала."
}
BATCH_SYNC_COMPLETED = {
    "en": "Batch syncing completed.",
    "es": "Sincronización por lotes completada.",
    "tr": "Toplu senkronizasyon tamamlandı.",
    "zh": "批量同步已完成。",
    "ru": "Пакетная синхронизация завершена."
}
PREPARING_SYNC = {
    "en": "Preparing {base_name}{file_extension} for automatic sync...",
    "es": "Preparando {base_name}{file_extension} para sincronización automática...",
    "tr": "Otomatik senkronizasyon için {base_name}{file_extension} hazırlanıyor...",
    "zh": "准备 {base_name}{file_extension} 进行自动同步...",
    "ru": "Подготовка {base_name}{file_extension} для автоматической синхронизации..."
}
CONVERTING_TTML = {
    "en": "Converting TTML/DFXP/ITT to SRT...",
    "es": "Convirtiendo TTML/DFXP/ITT a SRT...",
    "tr": "TTML/DFXP/ITT uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 TTML/DFXP/ITT 转换为 SRT...",
    "ru": "Преобразование TTML/DFXP/ITT в SRT..."
}
CONVERTING_VTT = {
    "en": "Converting VTT to SRT...",
    "es": "Convirtiendo VTT a SRT...",
    "tr": "VTT uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 VTT 转换为 SRT...",
    "ru": "Преобразование VTT в SRT..."
}
CONVERTING_SBV = {
    "en": "Converting SBV to SRT...",
    "es": "Convirtiendo SBV a SRT...",
    "tr": "SBV uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 SBV 转换为 SRT...",
    "ru": "Преобразование SBV в SRT..."
}
CONVERTING_SUB = {
    "en": "Converting SUB to SRT...",
    "es": "Convirtiendo SUB a SRT...",
    "tr": "SUB uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 SUB 转换为 SRT...",
    "ru": "Преобразование SUB в SRT..."
}
CONVERTING_ASS = {
    "en": "Converting ASS/SSA to SRT...",
    "es": "Convirtiendo ASS/SSA a SRT...",
    "tr": "ASS/SSA uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 ASS/SSA 转换为 SRT...",
    "ru": "Преобразование ASS/SSA в SRT..."
}
CONVERTING_STL = {
    "en": "Converting STL to SRT...",
    "es": "Convirtiendo STL a SRT...",
    "tr": "STL uzantısı SRT'ye dönüştürülüyor...",
    "zh": "将 STL 转换为 SRT...",
    "ru": "Преобразование STL в SRT..."
}
CONVERSION_NOT_SUPPORTED = {
    "en": "Error: Conversion for {file_extension} is not supported.",
    "es": "Error: La conversión para {file_extension} no está soportada.",
    "tr": "Hata: {file_extension} dönüştürme desteklenmiyor.",
    "zh": "错误：不支持 {file_extension} 的转换。",
    "ru": "Ошибка: Конвертация для {file_extension} не поддерживается."
}
RETRY_ENCODING_MSG = {
    "en": "Previous sync failed. Retrying with pre-detected encodings...",
    "es": "La sincronización anterior falló. Reintentando con codificaciones pre-detectadas...",
    "tr": "Önceki senkronizasyon başarısız oldu. Önceden tespit edilen kodlamalarla yeniden deneniyor...",
    "zh": "上一次同步失败。正在使用预检测的编码重试...",
    "ru": "Предыдущая синхронизация не удалась. Повторная попытка с предварительно обнаруженными кодировками..."
}
ALASS_SPEED_OPTIMIZATION_LOG = {
    "en": "Disabled: Speed optimization...",
    "es": "Deshabilitado: Optimización de velocidad...",
    "tr": "Devre dışı: Hız optimizasyonu...",
    "zh": "已禁用：速度优化...",
    "ru": "Отключено: Оптимизация скорости..."
}
ALASS_DISABLE_FPS_GUESSING_LOG = {
    "en": "Disabled: FPS guessing...",
    "es": "Deshabilitado: Adivinación de FPS...",
    "tr": "Devre dışı: FPS tahmini...",
    "zh": "已禁用：FPS 猜测...",
    "ru": "Отключено: Угадывание FPS..."
}
CHANGING_ENCODING_MSG = {
    "en": "Encoding of the synced subtitle does not match the original subtitle's encoding. Changing from {synced_subtitle_encoding} to {encoding_inc}...",
    "es": "La codificación del subtítulo sincronizado no coincide con la codificación del subtítulo original. Cambiando de {synced_subtitle_encoding} a {encoding_inc}...",
    "tr": "Senkronize altyazının kodlaması, orijinal altyazının kodlamasıyla eşleşmiyor. {synced_subtitle_encoding} kodlamasından {encoding_inc} kodlamasına geçiliyor...",
    "zh": "同步字幕的编码与原始字幕的编码不匹配。正在从 {synced_subtitle_encoding} 更改为 {encoding_inc}...",
    "ru": "Кодировка синхронизированных субтитров не совпадает с кодировкой оригинальных субтитров. Изменение с {synced_subtitle_encoding} на {encoding_inc}..."
}
ENCODING_CHANGED_MSG = {
    "en": "Encoding changed successfully.",
    "es": "Codificación cambiada con éxito.",
    "tr": "Kodlama başarıyla değiştirildi.",
    "zh": "编码更改成功。",
    "ru": "Кодировка успешно изменена."
}
SYNC_SUCCESS_COUNT = {
    "en": "Successfully synced {success_count} subtitle file(s).",
    "es": "Se sincronizaron correctamente {success_count} archivo(s) de subtítulos.",
    "tr": "{success_count} altyazı dosyası başarıyla senkronize edildi.",
    "zh": "成功同步了 {success_count} 个字幕文件。",
    "ru": "Успешно синхронизировано {success_count} файл(ов) субтитров."
}
SYNC_FAILURE_COUNT = {
    "en": "Failed to sync {failure_count} subtitle file(s).",
    "es": "No se pudo sincronizar {failure_count} archivo(s) de subtítulos.",
    "tr": "{failure_count} altyazı dosyası senkronize edilemedi.",
    "zh": "未能同步 {failure_count} 个字幕文件。",
    "ru": "Не удалось синхронизировать {failure_count} файл(ов) субтитров."
}
SYNC_FAILURE_COUNT_BATCH = {
    "en": "Failed to sync {failure_count} pair(s):",
    "es": "No se pudo sincronizar {failure_count} par(es):",
    "tr": "{failure_count} çift senkronize edilemedi:",
    "zh": "未能同步 {failure_count} 对：",
    "ru": "Не удалось синхронизировать {failure_count} пар(ы):"
}
ERROR_CHANGING_ENCODING_MSG = {
    "en": "Error changing encoding: {error_message}\n",
    "es": "Error al cambiar la codificación: {error_message}\n",
    "tr": "Kodlama değiştirilirken hata: {error_message}\n",
    "zh": "更改编码时出错：{error_message}\n",
    "ru": "Ошибка при изменении кодировки: {error_message}\n"
}
BACKUP_CREATED = {
    "en": "A backup of the existing subtitle file has been saved to: {output_subtitle_file}.",
    "es": "Se ha guardado una copia de seguridad del archivo de subtítulos existente en: {output_subtitle_file}.",
    "tr": "Mevcut altyazı dosyasının bir yedeği kaydedildi: {output_subtitle_file}.",
    "zh": "现有字幕文件的备份已保存到：{output_subtitle_file}。",
    "ru": "Резервная копия существующего файла субтитров сохранена в: {output_subtitle_file}."
}
CHECKING_SUBTITLE_STREAMS = {
    "en": "Checking the video for subtitle streams...",
    "es": "Verificando el video para flujos de subtítulos...",
    "tr": "Videodaki altyazı akışları kontrol ediliyor...",
    "zh": "正在检查视频的字幕流...",
    "ru": "Проверка видео на наличие потоков субтитров..."
}
FOUND_COMPATIBLE_SUBTITLES = {
    "en": "Found {count} compatible subtitles to extract.\nExtracting subtitles to folder: {output_folder}...",
    "es": "Se encontraron {count} subtítulos compatibles para extraer.\nExtrayendo subtítulos en la carpeta: {output_folder}...",
    "tr": "Çıkartılacak {count} uyumlu altyazı bulundu.\nAltyazılar şu klasöre çıkartılıyor: {output_folder}...",
    "zh": "找到了 {count} 个兼容的字幕要提取。\n正在提取字幕到文件夹：{output_folder}...",
    "ru": "Найдено {count} совместимых субтитров для извлечения.\nИзвлечение субтитров в папку: {output_folder}..."
}
NO_COMPATIBLE_SUBTITLES = {
    "en": "No compatible subtitles found to extract.",
    "es": "No se encontraron subtítulos compatibles para extraer.",
    "tr": "Çıkartılacak uyumlu altyazı bulunamadı.",
    "zh": "找不到要提取的兼容字幕。",
    "ru": "Совместимые субтитры для извлечения не найдены."
}
SUCCESSFULLY_EXTRACTED = {
    "en": "Successfully extracted: {filename}.",
    "es": "Extraído exitosamente: {filename}.",
    "tr": "Başarıyla çıkartıldı: {filename}.",
    "zh": "成功提取：{filename}。",
    "ru": "Успешно извлечено: {filename}."
}
CHOOSING_BEST_SUBTITLE = {
    "en": "Selecting the best subtitle for syncing...",
    "es": "Seleccionando el mejor subtítulo para sincronizar...",
    "tr": "Senkronizasyon için en iyi altyazı seçiliyor...",
    "zh": "选择最佳字幕进行同步...",
    "ru": "Выбор лучшего субтитра для синхронизации..."
}
CHOSEN_SUBTITLE = {
    "en": "Selected: {filename} with timestamp difference: {score}",
    "es": "Seleccionado: {filename} con diferencia de marca de tiempo: {score}",
    "tr": "Seçildi: {filename}, zaman damgası farkı: {score}",
    "zh": "已选择：{filename}，时间戳差异：{score}",
    "ru": "Выбрано: {filename} с разницей во времени: {score}"
}
FAILED_TO_EXTRACT_SUBTITLES = {
    "en": "Failed to extract subtitles. Error: {error}",
    "es": "No se pudieron extraer los subtítulos. Error: {error}",
    "tr": "Altyazılar çıkarılamadı. Hata: {error}",
    "zh": "提取字幕失败。错误：{error}",
    "ru": "Не удалось извлечь субтитры. Ошибка: {error}"
}
USED_THE_LONGEST_SUBTITLE = {
    "en": "Used the longest subtitle file because parse_timestamps failed.",
    "es": "Se usó el archivo de subtítulos más largo porque parse_timestamps falló.",
    "tr": "parse_timestamps başarısız olduğu için en uzun altyazı dosyası kullanıldı.",
    "zh": "使用最长的字幕文件，因为 parse_timestamps 失败。",
    "ru": "Использован самый длинный файл субтитров, потому что parse_timestamps завершился с ошибкой."
}
DELETING_EXTRACTED_SUBTITLE_FOLDER = {
    "en": "Deleting the extracted subtitles folder...",
    "es": "Eliminando la carpeta de subtítulos extraídos...",
    "tr": "Çıkarılan altyazılar klasörü siliniyor...",
    "zh": "删除提取的字幕文件夹...",
    "ru": "Удаление папки извлеченных субтитров..."
}
DELETING_CONVERTED_SUBTITLE = {
    "en": "Deleting the converted subtitle file...",
    "es": "Eliminando el archivo de subtítulos convertido...",
    "tr": "Dönüştürülmüş altyazı dosyası siliniyor...",
    "zh": "正在检查视频的字幕流...",
    "ru": "Удаление преобразованного файла субтитров..."

}
ADDED_FILES_TEXT = {
    "en": "Added {added_files} files",
    "es": "Agregado {added_files} archivos",
    "tr": "{added_files} dosya eklendi",
    "zh": "添加了 {added_files} 个文件",
    "ru": "Добавлено {added_files} файлов"
}
SKIPPED_DUPLICATE_FILES_TEXT = {
    "en": "Skipped {skipped_files} duplicate files",
    "es": "Omitido {skipped_files} archivos duplicados",
    "tr": "{skipped_files} yinelenen dosya atlandı",
    "zh": "跳过 {skipped_files} 个重复文件",
    "ru": "Пропущено {skipped_files} дублированных файлов"
}
SKIPPED_OTHER_LIST_FILES_TEXT = {
    "en": "Skipped {duplicate_in_other} files already in other list",
    "es": "Omitido {duplicate_in_other} archivos ya en la otra lista",
    "tr": "Diğer listede bulunan {duplicate_in_other} dosya atlandı",
    "zh": "跳过 {duplicate_in_other} 个已在其他列表中的文件",
    "ru": "Пропущено {duplicate_in_other} файлов, уже находящихся в другом списке"
}
SKIPPED_SEASON_EPISODE_DUPLICATES_TEXT = {
    "en": "Skipped {len} files with duplicate season/episode numbers",
    "es": "Omitido {len} archivos con números de temporada/episodio duplicados",
    "tr": "Aynı sezon/bölüm numaralarına sahip {len} dosya atlandı",
    "zh": "跳过 {len} 个具有重复季/集编号的文件",
    "ru": "Пропущено {len} файлов с дублирующимися номерами сезона/эпизода"
}
SKIPPED_INVALID_FORMAT_FILES_TEXT = {
    "en": "Skipped {len} files without valid episode format",
    "es": "Omitido {len} archivos sin formato de episodio válido",
    "tr": "Geçerli bölüm formatı olmayan {len} dosya atlandı",
    "zh": "跳过 {len} 个没有有效集格式的文件",
    "ru": "Пропущено {len} файлов без действительного формата эпизода"
}
NO_FILES_SELECTED = {
    "en": "No files selected.",
    "es": "No se seleccionaron archivos.",
    "tr": "Dosya seçilmedi.",
    "zh": "未选择文件。",
    "ru": "Файлы не выбраны."
}
NO_ITEM_SELECTED_TO_REMOVE = {
    "en": "No item selected to remove.",
    "es": "No se seleccionó ningún elemento para eliminar.",
    "tr": "Kaldırmak için öğe seçilmedi.",
    "zh": "未选择要删除的项目。",
    "ru": "Не выбран элемент для удаления."
}
NO_FILES_SELECTED_TO_SHOW_PATH = {
    "en": "No file selected to show path.",
    "es": "No se seleccionó ningún archivo para mostrar la ruta.",
    "tr": "Yolu göstermek için dosya seçilmedi.",
    "zh": "未选择要显示路径的文件。",
    "ru": "Файл не выбран для отображения пути."
}
REMOVED_ITEM = {
    "en": "Removed item.",
    "es": "Elemento eliminado.",
    "tr": "Öğe kaldırıldı.",
    "zh": "已删除项目。",
    "ru": "Элемент удален."
}
FILES_MUST_CONTAIN_PATTERNS = {
    "en": "Files must contain patterns like S01E01, 1x01 etc.",
    "es": "Los archivos deben contener patrones como S01E01, 1x01 etc.",
    "tr": "Dosyalar S01E01, 1x01 vb. kalıplar içermelidir.",
    "zh": "文件必须包含 S01E01、1x01 等模式。",
    "ru": "Файлы должны содержать шаблоны типа S01E01, 1x01 и т. д."
}
NO_VALID_SUBTITLE_FILES = {
    "en": "No valid subtitle files found.",
    "es": "No se encontraron archivos de subtítulos válidos.",
    "tr": "Geçerli altyazı dosyası bulunamadı.",
    "zh": "找不到有效的字幕文件。",
    "ru": "Действительные файлы субтитров не найдены."
}
NO_SUBTITLE_PAIRS_TO_PROCESS = {
    "en": "No subtitle pairs to process.",
    "es": "No hay pares de subtítulos para procesar.",
    "tr": "İşlenecek altyazı çifti yok.",
    "zh": "没有要处理的字幕对。",
    "ru": "Нет пар субтитров для обработки."
}
NO_MATCHING_SUBTITLE_PAIRS_FOUND = {
    "en": "No matching subtitle pairs found.",
    "es": "No se encontraron pares de subtítulos coincidentes.",
    "tr": "Eşleşen altyazı çifti bulunamadı.",
    "zh": "找不到匹配的字幕对。",
    "ru": "Совпадающие пары субтитров не найдены."
}
NO_VALID_SUBTITLE_PAIRS_TO_PROCESS = {
    "en": "No valid subtitle pairs to process.",
    "es": "No hay pares de subtítulos válidos para procesar.",
    "tr": "İşlenecek geçerli altyazı çifti yok.",
    "zh": "没有有效的字幕对要处理。",
    "ru": "Нет действительных пар субтитров для обработки."
}
for name, obj in list(globals().items()):
    if isinstance(obj, dict) and name != "TranslationDict":
        globals()[name] = TranslationDict(obj)