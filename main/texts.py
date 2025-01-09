# Tooltip texts for checkboxes
PROGRAM_NAME = "AutoSubSync"
TOOLTIP_SAVE_TO_DESKTOP = {
    "en": "Check this box if you want to save the new subtitle to your Desktop. If unchecked, it will be saved in the original subtitle's folder.",
    "es": "Marque esta casilla si desea guardar el nuevo subtítulo en su escritorio. Si no está marcado, se guardará en la carpeta del subtítulo original.",
    "tr": "Yeni altyazıyı masaüstüne kaydetmek istiyorsanız bu kutuyu işaretleyin. İşaretlenmezse, orijinal altyazının klasörüne kaydedilecektir."
}
TOOLTIP_REPLACE_ORIGINAL = {
    "en": "Check this box if you want to replace the original subtitle file with the new one. Please be careful. It will overwrite the current subtitle.",
    "es": "Marque esta casilla si desea reemplazar el archivo de subtítulos original con el nuevo. Por favor, tenga cuidado. Sobrescribirá el subtítulo actual.",
    "tr": "Orijinal altyazı dosyasını yenisiyle değiştirmek istiyorsanız bu kutuyu işaretleyin. Lütfen dikkatli olun. Mevcut altyazının üzerine yazacaktır."
}
TOOLTIP_GSS = {
    "en": "--gss: Use golden-section search to find the optimal ratio between video and subtitle framerates (by default, only a few common ratios are evaluated)",
    "es": "--gss: Utilice la búsqueda de sección áurea para encontrar la proporción óptima entre las tasas de fotogramas de video y subtítulos (por defecto, solo se evalúan algunas proporciones comunes)",
    "tr": "--gss: Video ve altyazı kare hızları arasındaki en uygun oranı bulmak için altın oran aramasını kullanın (varsayılan olarak, yalnızca birkaç yaygın oran değerlendirilir)"
}
TOOLTIP_VAD = {
    "en": "--vad=auditok: Auditok can sometimes work better in the case of low-quality audio than WebRTC's VAD. Auditok does not specifically detect voice, but instead detects all audio; this property can yield suboptimal syncing behavior when a proper VAD can work well, but can be effective in some cases.",
    "es": "--vad=auditok: Auditok a veces puede funcionar mejor en el caso de audio de baja calidad que el VAD de WebRTC. Auditok no detecta específicamente la voz, sino que detecta todo el audio; esta propiedad puede producir un comportamiento de sincronización subóptimo cuando un VAD adecuado puede funcionar bien, pero puede ser efectivo en algunos casos.",
    "tr": "--vad=auditok: Auditok, düşük kaliteli ses durumunda bazen WebRTC'nin VAD'sinden daha iyi çalışabilir. Auditok, özellikle sesi algılamaz, bunun yerine tüm sesleri algılar; bu özellik, uygun bir VAD'nin iyi çalışabileceği durumlarda optimal olmayan senkronizasyon davranışına neden olabilir, ancak bazı durumlarda etkili olabilir."
}
TOOLTIP_FRAMERATE = {
    "en": "--no-fix-framerate: If specified, ffsubsync will not attempt to correct a framerate mismatch between reference and subtitles. This can be useful when you know that the video and subtitle framerates are same, only the subtitles are out of sync.",
    "es": "--no-fix-framerate: Si se especifica, ffsubsync no intentará corregir una discrepancia de velocidad de fotogramas entre la referencia y los subtítulos. Esto puede ser útil cuando sabes que las tasas de fotogramas de video y subtítulos son las mismas, solo los subtítulos están desincronizados.",
    "tr": "--no-fix-framerate: Belirtilirse, ffsubsync referans ve altyazılar arasındaki kare hızı uyumsuzluğunu düzeltmeye çalışmaz. Bu, video ve altyazı kare hızlarının aynı olduğunu bildiğinizde, yalnızca altyazıların senkronize olmadığında yararlı olabilir."
}
TOOLTIP_ALASS_SPEED_OPTIMIZATION = {
    "en": "--speed optimization 0: Disable speed optimization for better accuracy. This will increase the processing time.",
    "es": "--speed optimization 0: Deshabilite la optimización de velocidad para una mejor precisión. Esto aumentará el tiempo de procesamiento.",
    "tr": "--speed optimization 0: Daha iyi doğruluk için hız optimizasyonunu devre dışı bırakın. Bu, işlem süresini artıracaktır."
}
TOOLTIP_ALASS_DISABLE_FPS_GUESSING = {
    "en": "--disable-fps-guessing: Disables guessing and correcting of framerate differences between reference file and input file.",
    "es": "--disable-fps-guessing: Deshabilita la adivinación y corrección de diferencias de velocidad de fotogramas entre el archivo de referencia y el archivo de entrada.",
    "tr": "--disable-fps-guessing: Referans dosya ile giriş dosyası arasındaki kare hızı farklarını tahmin etmeyi ve düzeltmeyi devre dışı bırakır."
}
TOOLTIP_TEXT_ACTION_MENU_AUTO = {
    "en": "Choose what to do with the synchronized subtitle file(s). (Existing subtitle files will be backed up in the same folder, if they need to be replaced.)",
    "es": "Elija qué hacer con el/los archivo(s) de subtítulos sincronizados. (Los archivos de subtítulos existentes se respaldarán en la misma carpeta, si necesitan ser reemplazados.)",
    "tr": "Senkronize edilmiş altyazı dosyası/dosyaları ile ne yapılacağını seçin. (Mevcut altyazı dosyaları değiştirilmesi gerekiyorsa aynı klasörde yedeklenecektir.)"
}
TOOLTIP_TEXT_SYNC_TOOL_MENU_AUTO = {
    "en": "Select the tool to use for synchronization.",
    "es": "Seleccione la herramienta a utilizar para la sincronización.",
    "tr": "Senkronizasyon için kullanılacak aracı seçin."
}
UPDATE_AVAILABLE_TITLE = {
    "en": "Update Available",
    "es": "Actualización Disponible",
    "tr": "Güncelleme Mevcut"
}
UPDATE_AVAILABLE_TEXT = {
    "en": "A new version ({latest_version}) is available. Do you want to update?",
    "es": "Una nueva versión ({latest_version}) está disponible. ¿Quieres actualizar?",
    "tr": "Yeni bir sürüm ({latest_version}) mevcut. Güncellemek istiyor musunuz?"
}
NOTIFY_ABOUT_UPDATES_TEXT = {
    "en": "Notify about updates",
    "es": "Notificar sobre actualizaciones",
    "tr": "Güncellemeler hakkında bilgilendir"
}
LANGUAGE_LABEL_TEXT = {
    "en": "Language",
    "es": "Idioma",
    "tr": "Dil"
}
TAB_AUTOMATIC_SYNC = {
    "en": 'Automatic Sync',
    "es": 'Sinc. Automática',
    "tr": 'Otomatik Senkr.'
}
TAB_MANUAL_SYNC = {
    "en": 'Manual Sync',
    "es": 'Sinc. Manual',
    "tr": 'Manuel Senk.'
}
CANCEL_TEXT = {
    "en": 'Cancel',
    "es": 'Cancelar',
    "tr": 'İptal'
}
GENERATE_AGAIN_TEXT = {
    "en": 'Generate Again',
    "es": 'Generar de Nuevo',
    "tr": 'Tekrar Oluştur'
}
GO_BACK = {
    "en": 'Go Back',
    "es": 'Regresar',
    "tr": 'Geri Dön'
}
BATCH_MODE_TEXT = {
    "en": 'Batch Mode',
    "es": 'Modo por Lotes',
    "tr": 'Toplu Mod'
}
NORMAL_MODE_TEXT = {
    "en": 'Normal Mode',
    "es": 'Modo Normal',
    "tr": 'Normal Mod'
}
START_AUTOMATIC_SYNC_TEXT = {
    "en": 'Start Automatic Sync',
    "es": 'Iniciar Sinc. Automática',
    "tr": 'Otomatik Senkr. Başlat'
}
START_BATCH_SYNC_TEXT = {
    "en": 'Start Batch Sync',
    "es": 'Iniciar Sincr. por Lotes',
    "tr": 'Toplu Senkr. Başlat'
}
BATCH_INPUT_TEXT = {
    "en": "Drag and drop multiple files/folders here or click to browse.\n\n(Videos and subtitles that have the same filenames will be\n paired automatically. You need to pair others manually.)",
    "es": "Arrastre y suelte varios archivos/carpetas aquí o haga clic para buscar.\n\n(Los videos y subtítulos que tienen los mismos nombres de archivo se\n emparejarán automáticamente. Debe emparejar otros manualmente.)",
    "tr": "Birden fazla dosya/klasörü buraya sürükleyip bırakın veya göz atmak için tıklayın.\n\n(Aynı dosya adlarına sahip videolar ve altyazılar\n otomatik olarak eşleştirilecektir. Diğerlerini manuel olarak eşleştirmeniz gerekir.)"
}
BATCH_INPUT_LABEL_TEXT = {
    "en": "Batch Processing Mode",
    "es": "Modo de Procesamiento por Lotes",
    "tr": "Toplu İşleme Modu"
}
SHIFT_SUBTITLE_TEXT = {
    "en": 'Shift Subtitle',
    "es": 'Desplazar Subtítulo',
    "tr": 'Altyazıyı Kaydır'
}
LABEL_SHIFT_SUBTITLE = {
    "en": "Shift subtitle by (milliseconds):",
    "es": "Desplazar subtítulo por (milisegundos):",
    "tr": "Altyazıyı şu kadar kaydır (milisaniye):"
}
REPLACE_ORIGINAL_TITLE = {
    "en": "Subtitle Change Confirmation",
    "es": "Confirmación de Cambio de Subtítulo",
    "tr": "Altyazı Değişikliği Onayı"
}
REPLACE_ORIGINAL_TEXT = {
    "en": "Adjusting again by {milliseconds}ms, will make a total difference of {total_shifted}ms. Proceed?",
    "es": "Ajustar nuevamente por {milliseconds}ms, hará una diferencia total de {total_shifted}ms. ¿Proceder?",
    "tr": "{milliseconds}ms kadar yeniden ayarlamak, toplamda {total_shifted}ms fark yaratacaktır. Devam edilsin mi?"
}
FILE_EXISTS_TITLE = {
    "en": "File Exists",
    "es": "El Archivo Existe",
    "tr": "Dosya Mevcut"
}
FILE_EXISTS_TEXT = {
    "en": "A file with the name '{filename}' already exists. Do you want to replace it?",
    "es": "Un archivo con el nombre '{filename}' ya existe. ¿Desea reemplazarlo?",
    "tr": "'{filename}' adında bir dosya zaten var. Değiştirmek istiyor musunuz?"
}
ALREADY_SYNCED_FILES_TITLE = {
    "en": "Already Synced Files Detected",
    "es": "Archivos Ya Sincronizados Detectados",
    "tr": "Zaten Senkronize Edilmiş Dosyalar Tespit Edildi"
}
ALREADY_SYNCED_FILES_MESSAGE = {
    "en": "Detected {count} subtitle(s) already synced, because there are subtitles that have 'autosync_' prefix in the same folder with same filenames. Do you want to skip processing them?\n\n(Even if you say no, your existing subtitles will not be overwritten. The subtitle will be saved with different name.)",
    "es": "Se detectaron {count} subtítulo(s) ya sincronizados, porque hay subtítulos que tienen el prefijo 'autosync_' en la misma carpeta con los mismos nombres de archivo. ¿Desea omitir su procesamiento?\n\n(Incluso si dice que no, sus subtítulos existentes no se sobrescribirán. El subtítulo se guardará con un nombre diferente.)",
    "tr": "Aynı klasörde aynı dosya adlarına sahip 'autosync_' öneki olan altyazılar olduğu için {count} altyazı zaten senkronize edilmiş olarak tespit edildi. İşlemeyi atlamak istiyor musunuz?\n\n(Hayır deseniz bile, mevcut altyazılarınız üzerine yazılmayacaktır. Altyazı farklı bir adla kaydedilecektir.)"
}
SUBTITLE_INPUT_TEXT = {
    "en": "Drag and drop the unsynchronized subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de subtítulos no sincronizado aquí o haga clic para buscar.",
    "tr": "Senkronize edilmemiş altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın."
}
VIDEO_INPUT_TEXT = {
    "en": "Drag and drop video or reference subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de video o subtítulos de referencia aquí o haga clic para buscar.",
    "tr": "Video veya referans altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın."
}
LABEL_DROP_BOX = {
    "en": "Drag and drop subtitle file here or click to browse.",
    "es": "Arrastre y suelte el archivo de subtítulos aquí o haga clic para buscar.",
    "tr": "Altyazı dosyasını buraya sürükleyip bırakın veya göz atmak için tıklayın."
}
WARNING = {
    "en": "Warning",
    "es": "Advertencia",
    "tr": "Uyarı"
}
CONFIRM_RESET_MESSAGE = {
    "en": "Are you sure you want to reset settings to default values?",
    "es": "¿Está seguro de que desea restablecer la configuración a los valores predeterminados?",
    "tr": "Ayarları varsayılan değerlere sıfırlamak istediğinizden emin misiniz?"
}
TOGGLE_KEEP_CONVERTED_SUBTITLES_WARNING = {
    "en": 'Subtitles with "converted_subtitlefilename" in the output folder will be deleted automatically. Do you want to continue?',
    "es": 'Los subtítulos con "converted_subtitlefilename" en la carpeta de salida se eliminarán automáticamente. ¿Desea continuar?',
    "tr": 'Çıktı klasöründe "converted_subtitlefilename" olan altyazılar otomatik olarak silinecektir. Devam etmek istiyor musunuz?'
}
TOGGLE_KEEP_EXTRACTED_SUBTITLES_WARNING = {
    "en": 'Folders with "extracted_subtitles_videofilename" in the output folder will be deleted automatically. Do you want to continue?',
    "es": 'Las carpetas con "extracted_subtitles_videofilename" en la carpeta de salida se eliminarán automáticamente. ¿Desea continuar?',
    "tr": 'Çıktı klasöründe "extracted_subtitles_videofilename" olan klasörler otomatik olarak silinecektir. Devam etmek istiyor musunuz?'
}
BACKUP_SUBTITLES_BEFORE_OVERWRITING_WARNING = {
    "en": "Existing subtitle files will not be backed up before overwriting. Do you want to continue?",
    "es": "Los archivos de subtítulos existentes no se respaldarán antes de sobrescribir. ¿Desea continuar?",
    "tr": "Mevcut altyazı dosyaları üzerine yazılmadan önce yedeklenmeyecektir. Devam etmek istiyor musunuz?"
}
PROMPT_ADDITIONAL_FFSUBSYNC_ARGS = {
    "en": "Enter additional arguments for ffsubsync:",
    "es": "Ingrese argumentos adicionales para ffsubsync:",
    "tr": "ffsubsync için ek argümanlar girin:"
}
PROMPT_ADDITIONAL_ALASS_ARGS = {
    "en": "Enter additional arguments for alass:",
    "es": "Ingrese argumentos adicionales para alass:",
    "tr": "alass için ek argümanlar girin:"
}
LABEL_ADDITIONAL_FFSUBSYNC_ARGS = {
    "en": "Additional arguments for ffsubsync",
    "es": "Argumentos adicionales para ffsubsync",
    "tr": "ffsubsync için ek argümanlar"
}
LABEL_ADDITIONAL_ALASS_ARGS = {
    "en": "Additional arguments for alass",
    "es": "Argumentos adicionales para alass",
    "tr": "alass için ek argümanlar"
}
LABEL_CHECK_VIDEO_FOR_SUBTITLE_STREAM = {
    "en": "Check video for subtitle streams in alass",
    "es": "Verificar video para flujos de subtítulos en alass",
    "tr": "alass'ta altyazı akışları için videoyu kontrol et"
}
LABEL_BACKUP_SUBTITLES = {
    "en": "Backup subtitles before overwriting",
    "es": "Respaldar subtítulos antes de sobrescribir",
    "tr": "Üzerine yazmadan önce altyazıları yedekle"
}
LABEL_KEEP_CONVERTED_SUBTITLES = {
    "en": "Keep converted subtitles",
    "es": "Mantener subtítulos convertidos",
    "tr": "Dönüştürülmüş altyazıları sakla"
}
LABEL_KEEP_EXTRACTED_SUBTITLES = {
    "en": "Keep extracted subtitles",
    "es": "Mantener subtítulos extraídos",
    "tr": "Çıkarılan altyazıları sakla"
}
LABEL_REMEMBER_THE_CHANGES = {
    "en": "Remember the changes",
    "es": "Recordar los cambios",
    "tr": "Değişiklikleri hatırla"
}
LABEL_RESET_TO_DEFAULT_SETTINGS = {
    "en": "Reset to default settings",
    "es": "Restablecer a la configuración predeterminada",
    "tr": "Varsayılan ayarlara sıfırla"
}
SYNC_TOOL_FFSUBSYNC = {
    "en": "ffsubsync",
    "es": "ffsubsync",
    "tr": "ffsubsync"
}
SYNC_TOOL_ALASS = {
    "en": "alass",
    "es": "alass",
    "tr": "alass"
}
OPTION_SAVE_NEXT_TO_SUBTITLE = {
    "en": "Save next to subtitle",
    "es": "Guardar junto al subtítulo",
    "tr": "Altyazının yanına kaydet"
}
OPTION_SAVE_NEXT_TO_VIDEO = {
    "en": "Save next to video",
    "es": "Guardar junto al video",
    "tr": "Videonun yanına kaydet"
}
OPTION_SAVE_NEXT_TO_VIDEO_WITH_SAME_FILENAME = {
    "en": "Save next to video with same filename",
    "es": "Guardar junto al video con el mismo nombre de archivo",
    "tr": "Aynı dosya adıyla videonun yanına kaydet"
}
OPTION_SAVE_TO_DESKTOP = {
    "en": "Save to Desktop",
    "es": "Guardar en el escritorio",
    "tr": "Masaüstüne kaydet"
}
OPTION_REPLACE_ORIGINAL_SUBTITLE = {
    "en": "Replace original subtitle",
    "es": "Reemplazar subtítulo original",
    "tr": "Orijinal altyazıyı değiştir"
}
OPTION_SELECT_DESTINATION_FOLDER = {
    "en": "Select destination folder",
    "es": "Seleccionar carpeta de destino",
    "tr": "Hedef klasörü seç"
}
CHECKBOX_NO_FIX_FRAMERATE = {
    "en": "Don't fix framerate",
    "es": "No corregir la velocidad de fotogramas",
    "tr": "Kare hızını düzeltme"
}
CHECKBOX_GSS = {
    "en": "Use golden-section search",
    "es": "Usar búsqueda de sección áurea",
    "tr": "Altın oran aramasını kullan"
}
CHECKBOX_VAD = {
    "en": "Use auditok instead of WebRTC's VAD",
    "es": "Usar auditok en lugar del VAD de WebRTC",
    "tr": "WebRTC'nin VAD'si yerine auditok kullan"
}
LABEL_SPLIT_PENALTY = {
    "en": "Split Penalty (Default: 7, Recommended: 5-20, No splits: 0)",
    "es": "Penalización por división (Predeterminado: 7, Recomendado: 5-20, Sin divisiones: 0)",
    "tr": "Bölme Cezası (Varsayılan: 7, Önerilen: 5-20, Bölme yok: 0)"
}
PAIR_FILES_TITLE = {
    "en": "Pair Files",
    "es": "Emparejar archivos",
    "tr": "Dosyaları Eşleştir"
}
PAIR_FILES_MESSAGE = {
    "en": "The subtitle and video have different filenames. Do you want to pair them?",
    "es": "El subtítulo y el video tienen nombres de archivo diferentes. ¿Quieres emparejarlos?",
    "tr": "Altyazı ve video farklı dosya adlarına sahip. Eşleştirmek istiyor musunuz?"
}
UNPAIRED_SUBTITLES_TITLE = {
    "en": "Unpaired Subtitles",
    "es": "Subtítulos no emparejados",
    "tr": "Eşleşmemiş Altyazılar"
}
UNPAIRED_SUBTITLES_MESSAGE = {
    "en": "There are {unpaired_count} unpaired subtitle(s). Do you want to add them as subtitles with [no video] tag?",
    "es": "Hay {unpaired_count} subtítulo(s) no emparejado(s). ¿Quieres agregarlos como subtítulos con la etiqueta [sin video]?",
    "tr": "{unpaired_count} eşleşmemiş altyazı var. Bunları [video yok] etiketiyle altyazı olarak eklemek istiyor musunuz?"
}
NO_VIDEO = {
    "en": "[no video]",
    "es": "[sin video]",
    "tr": "[video yok]"
}
NO_SUBTITLE = {
    "en": "[no subtitle]",
    "es": "[sin subtítulo]",
    "tr": "[altyazı yok]"
}
VIDEO_OR_SUBTITLE_TEXT = {
    "en": "Video or subtitle",
    "es": "Video o subtítulo",
    "tr": "Video veya altyazı"
}
VIDEO_INPUT_LABEL = {
    "en": "Video/Reference subtitle",
    "es": "Video/Subtítulo de referencia",
    "tr": "Video/Referans altyazı"
}
SUBTITLE_INPUT_LABEL = {
    "en": "Subtitle",
    "es": "Subtítulo",
    "tr": "Altyazı"
}
SUBTITLE_FILES_TEXT = {
    "en": "Subtitle files",
    "es": "Archivos de subtítulos",
    "tr": "Altyazı dosyaları"
}
CONTEXT_MENU_REMOVE = {
    "en": "Remove",
    "es": "Eliminar",
    "tr": "Kaldır"
}
CONTEXT_MENU_CHANGE = {
    "en": "Change",
    "es": "Cambiar",
    "tr": "Değiştir"
}
CONTEXT_MENU_ADD_PAIR = {
    "en": "Add Pair",
    "es": "Agregar par",
    "tr": "Çift Ekle"
}
CONTEXT_MENU_CLEAR_ALL = {
    "en": "Clear All",
    "es": "Limpiar todo",
    "tr": "Hepsini Temizle"
}
CONTEXT_MENU_SHOW_PATH = {
    "en": "Show path",
    "es": "Mostrar ruta",
    "tr": "Yolu göster"
}
BUTTON_ADD_FILES = {
    "en": "Add files",
    "es": "Agregar archivos",
    "tr": "Dosya ekle"
}
MENU_ADD_FOLDER = {
    "en": "Add Folder",
    "es": "Agregar carpeta",
    "tr": "Klasör ekle"
}
MENU_ADD_MULTIPLE_FILES = {
    "en": "Add Multiple Files",
    "es": "Agregar múltiples archivos",
    "tr": "Çoklu Dosya Ekle"
}
MENU_ADD_REFERENCE_SUBITLE_SUBTITLE_PAIRIS = {
    "en": "Add Reference Subtitle/Subtitle Pairs",
    "es": "Agregar pares de subtítulos de referencia/subtítulos",
    "tr": "Referans Altyazı/Altyazı Çiftleri Ekle"
}
ALASS_SPEED_OPTIMIZATION_TEXT = {
    "en": "Disable speed optimization",
    "es": "Deshabilitar optimización de velocidad",
    "tr": "Hız optimizasyonunu devre dışı bırak"
}
ALASS_DISABLE_FPS_GUESSING_TEXT = {
    "en": "Disable FPS guessing",
    "es": "Deshabilitar adivinación de FPS",
    "tr": "FPS tahminini devre dışı bırak"
}
REF_DROP_TEXT = {
    "en": "Drag and drop reference subtitles here\nor click to browse.",
    "es": "Arrastre y suelte subtítulos de referencia aquí\no haga clic para buscar.",
    "tr": "Referans altyazıları buraya sürükleyip bırakın\nveya göz atmak için tıklayın."
}
SUB_DROP_TEXT = {
    "en": "Drag and drop subtitles here\nor click to browse.",
    "es": "Arrastre y suelte subtítulos aquí\no haga clic para buscar.",
    "tr": "Altyazıları buraya sürükleyip bırakın\nveya göz atmak için tıklayın."
}
REF_LABEL_TEXT = {
    "en": "Reference Subtitles",
    "es": "Subtítulos de referencia",
    "tr": "Referans Altyazılar"
}
SUB_LABEL_TEXT = {
    "en": "Subtitles",
    "es": "Subtítulos",
    "tr": "Altyazılar"
}
PROCESS_PAIRS = {
    "en": "Add Pairs",
    "es": "Agregar pares",
    "tr": "Çiftleri Ekle"
}
SYNC_TOOL_LABEL_TEXT = {
    "en": "Sync using",
    "es": "Sincr. con",
    "tr": "Senkr. aracı"
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
    Desteklenen kombinasyonlar: S01E01, S1E1, S01E1, S1E01, 1x01, 01x1, 01x01, 1x1"""
}
SUCCESS_LOG_TEXT = {
    "en": "Success! Subtitle shifted by {milliseconds} milliseconds and saved to: {new_subtitle_file}",
    "es": "¡Éxito! Subtítulo desplazado por {milliseconds} milisegundos y guardado en: {new_subtitle_file}",
    "tr": "Başarılı! Altyazı {milliseconds} milisaniye kaydırıldı ve kaydedildi: {new_subtitle_file}"
}
SYNC_SUCCESS_MESSAGE = {
    "en": "Success! Synchronized subtitle saved to: {output_subtitle_file}",
    "es": "¡Éxito! Subtítulo sincronizado guardado en: {output_subtitle_file}",
    "tr": "Başarılı! Senkronize edilmiş altyazı kaydedildi: {output_subtitle_file}"
}
ERROR_SAVING_SUBTITLE = {
    "en": "Error saving subtitle file: {error_message}",
    "es": "Error al guardar el archivo de subtítulos: {error_message}",
    "tr": "Altyazı dosyası kaydedilirken hata: {error_message}"
}
NON_ZERO_MILLISECONDS = {
    "en": "Please enter a non-zero value for milliseconds.",
    "es": "Por favor, ingrese un valor distinto de cero para milisegundos.",
    "tr": "Lütfen milisaniye için sıfır olmayan bir değer girin."
}
SELECT_ONLY_ONE_OPTION = {
    "en": "Please select only one option: Save to Desktop or Replace Original Subtitle.",
    "es": "Por favor, seleccione solo una opción: Guardar en el escritorio o Reemplazar el subtítulo original.",
    "tr": "Lütfen yalnızca bir seçenek seçin: Masaüstüne Kaydet veya Orijinal Altyazıyı Değiştir."
}
VALID_NUMBER_MILLISECONDS = {
    "en": "Please enter a valid number of milliseconds.",
    "es": "Por favor, ingrese un número válido de milisegundos.",
    "tr": "Lütfen geçerli bir milisaniye sayısı girin."
}
SELECT_SUBTITLE = {
    "en": "Please select a subtitle file.",
    "es": "Por favor, seleccione un archivo de subtítulos.",
    "tr": "Lütfen bir altyazı dosyası seçin."
}
SELECT_VIDEO = {
    "en": "Please select a video file.",
    "es": "Por favor, seleccione un archivo de video.",
    "tr": "Lütfen bir video dosyası seçin."
}
SELECT_VIDEO_OR_SUBTITLE = {
    "en": "Please select a video or reference subtitle.",
    "es": "Por favor, seleccione un video o subtítulo de referencia.",
    "tr": "Lütfen bir video veya referans altyazı seçin."
}
DROP_VIDEO_SUBTITLE_PAIR = {
    "en": "Please drop a video, subtitle or pair.",
    "es": "Por favor, suelte un video, subtítulo o par.",
    "tr": "Lütfen bir video, altyazı veya çift bırakın."
}
DROP_VIDEO_OR_SUBTITLE = {
    "en": "Please drop a video or reference subtitle file.",
    "es": "Por favor, suelte un archivo de video o subtítulo de referencia.",
    "tr": "Lütfen bir video veya referans altyazı dosyası bırakın."
}
DROP_SUBTITLE_FILE = {
    "en": "Please drop a subtitle file.",
    "es": "Por favor, suelte un archivo de subtítulos.",
    "tr": "Lütfen bir altyazı dosyası bırakın."
}
DROP_SINGLE_SUBTITLE_FILE = {
    "en": "Please drop a single subtitle file.",
    "es": "Por favor, suelte un solo archivo de subtítulos.",
    "tr": "Lütfen tek bir altyazı dosyası bırakın."
}
DROP_SINGLE_SUBTITLE_PAIR = {
    "en": "Please drop a single subtitle or pair.",
    "es": "Por favor, suelte un solo subtítulo o par.",
    "tr": "Lütfen tek bir altyazı veya çift bırakın."
}
SELECT_BOTH_FILES = {
    "en": "Please select both video/reference subtitle and subtitle file.",
    "es": "Por favor, seleccione tanto el archivo de video/subtítulo de referencia como el archivo de subtítulos.",
    "tr": "Lütfen hem video/referans altyazı hem de altyazı dosyasını seçin."
}
SELECT_DIFFERENT_FILES = {
    "en": "Please select different subtitle files.",
    "es": "Por favor, seleccione diferentes archivos de subtítulos.",
    "tr": "Lütfen farklı altyazı dosyaları seçin."
}
SUBTITLE_FILE_NOT_EXIST = {
    "en": "Subtitle file does not exist.",
    "es": "El archivo de subtítulos no existe.",
    "tr": "Altyazı dosyası mevcut değil."
}
VIDEO_FILE_NOT_EXIST = {
    "en": "Video file does not exist.",
    "es": "El archivo de video no existe.",
    "tr": "Video dosyası mevcut değil."
}
ERROR_LOADING_SUBTITLE = {
    "en": "Error loading subtitle file: {error_message}",
    "es": "Error al cargar el archivo de subtítulos: {error_message}",
    "tr": "Altyazı dosyası yüklenirken hata: {error_message}"
}
ERROR_CONVERT_TIMESTAMP = {
    "en": "Failed to convert timestamp '{timestamp}' for format '{format_type}'",
    "es": "Error al convertir la marca de tiempo '{timestamp}' para el formato '{format_type}'",
    "tr": "'{timestamp}' zaman damgası '{format_type}' formatına dönüştürülemedi"
}
ERROR_PARSING_TIME_STRING = {
    "en": "Error parsing time string '{time_str}'",
    "es": "Error al analizar la cadena de tiempo '{time_str}'",
    "tr": "'{time_str}' zaman dizesi ayrıştırılırken hata"
}
ERROR_PARSING_TIME_STRING_DETAILED = {
    "en": "Error parsing time string '{time_str}' for format '{format_type}': {error_message}",
    "es": "Error al analizar la cadena de tiempo '{time_str}' para el formato '{format_type}': {error_message}",
    "tr": "'{time_str}' zaman dizesi '{format_type}' formatı için ayrıştırılırken hata: {error_message}"
}
NO_FILES_TO_SYNC = {
    "en": "No files to sync. Please add files to the batch list.",
    "es": "No hay archivos para sincronizar. Por favor, agregue archivos a la lista de lotes.",
    "tr": "Senkronize edilecek dosya yok. Lütfen toplu listeye dosya ekleyin."
}
NO_VALID_FILE_PAIRS = {
    "en": "No valid file pairs to sync.",
    "es": "No hay pares de archivos válidos para sincronizar.",
    "tr": "Senkronize edilecek geçerli dosya çifti yok."
}
ERROR_PROCESS_TERMINATION = {
    "en": "Error occurred during process termination: {error_message}",
    "es": "Ocurrió un error durante la terminación del proceso: {error_message}",
    "tr": "İşlem sonlandırma sırasında hata oluştu: {error_message}"
}
AUTO_SYNC_CANCELLED = {
    "en": "Automatic synchronization cancelled.",
    "es": "Sincronización automática cancelada.",
    "tr": "Otomatik senkronizasyon iptal edildi."
}
BATCH_SYNC_CANCELLED = {
    "en": "Batch synchronization cancelled.",
    "es": "Sincronización por lotes cancelada.",
    "tr": "Toplu senkronizasyon iptal edildi."
}
NO_SYNC_PROCESS = {
    "en": "No synchronization process to cancel.",
    "es": "No hay proceso de sincronización para cancelar.",
    "tr": "İptal edilecek senkronizasyon işlemi yok."
}
INVALID_SYNC_TOOL = {
    "en": "Invalid sync tool selected.",
    "es": "Herramienta de sincronización inválida seleccionada.",
    "tr": "Geçersiz senkronizasyon aracı seçildi."
}
FAILED_START_PROCESS = {
    "en": "Failed to start process: {error_message}",
    "es": "Error al iniciar el proceso: {error_message}",
    "tr": "İşlem başlatılamadı: {error_message}"
}
ERROR_OCCURRED = {
    "en": "Error occurred: {error_message}",
    "es": "Ocurrió un error: {error_message}",
    "tr": "Hata oluştu: {error_message}"
}
ERROR_EXECUTING_COMMAND = {
    "en": "Error executing command: ",
    "es": "Error al ejecutar el comando: ",
    "tr": "Komut yürütülürken hata: "
}
DROP_VALID_FILES = {
    "en": "Please drop valid subtitle and video files.",
    "es": "Por favor, suelte archivos de subtítulos y video válidos.",
    "tr": "Lütfen geçerli altyazı ve video dosyalarını bırakın."
}
PAIRS_ADDED = {
    "en": "Added {count} pair{s}",
    "es": "Agregado {count} par{s}",
    "tr": "{count} çift eklendi"
}
UNPAIRED_FILES_ADDED = {
    "en": "Added {count} unpaired file{s}",
    "es": "Agregado {count} archivo{s} no emparejado{s}",
    "tr": "{count} eşleşmemiş dosya eklendi"
}
UNPAIRED_FILES = {
    "en": "{count} unpaired file{s}",
    "es": "{count} archivo{s} no emparejado{s}",
    "tr": "{count} eşleşmemiş dosya"
}
DUPLICATE_PAIRS_SKIPPED = {
    "en": "{count} duplicate pair{s} skipped",
    "es": "{count} par{es} duplicado{s} omitido{s}",
    "tr": "{count} yinelenen çift atlandı"
}
PAIR_ALREADY_EXISTS = {
    "en": "This pair already exists.",
    "es": "Este par ya existe.",
    "tr": "Bu çift zaten mevcut."
}
PAIR_ADDED = {
    "en": "Added 1 pair.",
    "es": "Agregado 1 par.",
    "tr": "1 çift eklendi."
}
SAME_FILE_ERROR = {
    "en": "Cannot use the same file for both inputs.",
    "es": "No se puede usar el mismo archivo para ambas entradas.",
    "tr": "Her iki giriş için de aynı dosya kullanılamaz."
}
PAIR_ALREADY_EXISTS = {
    "en": "This pair already exists. Please select a different file.",
    "es": "Este par ya existe. Por favor, seleccione un archivo diferente.",
    "tr": "Bu çift zaten mevcut. Lütfen farklı bir dosya seçin."
}
SUBTITLE_ADDED = {
    "en": "Subtitle added.",
    "es": "Subtítulo agregado.",
    "tr": "Altyazı eklendi."
}
VIDEO_ADDED = {
    "en": "Video/reference subtitle added.",
    "es": "Video/subtítulo de referencia agregado.",
    "tr": "Video/referans altyazı eklendi."
}
FILE_CHANGED = {
    "en": "File changed.",
    "es": "Archivo cambiado.",
    "tr": "Dosya değiştirildi."
}
SELECT_ITEM_TO_CHANGE = {
    "en": "Please select an item to change.",
    "es": "Por favor, seleccione un elemento para cambiar.",
    "tr": "Lütfen değiştirmek için bir öğe seçin."
}
SELECT_ITEM_TO_REMOVE = {
    "en": "Please select an item to remove.",
    "es": "Por favor, seleccione un elemento para eliminar.",
    "tr": "Lütfen kaldırmak için bir öğe seçin."
}
FILE_NOT_EXIST = {
    "en": "File specified in the argument does not exist.",
    "es": "El archivo especificado en el argumento no existe.",
    "tr": "Argümanda belirtilen dosya mevcut değil."
}
MULTIPLE_ARGUMENTS = {
    "en": "Multiple arguments provided. Please provide only one subtitle file path.",
    "es": "Se proporcionaron múltiples argumentos. Por favor, proporcione solo una ruta de archivo de subtítulos.",
    "tr": "Birden fazla argüman sağlandı. Lütfen yalnızca bir altyazı dosyası yolu sağlayın."
}
INVALID_FILE_FORMAT = {
    "en": "Invalid file format. Please provide a subtitle file.",
    "es": "Formato de archivo inválido. Por favor, proporcione un archivo de subtítulos.",
    "tr": "Geçersiz dosya formatı. Lütfen bir altyazı dosyası sağlayın."
}
INVALID_SYNC_TOOL_SELECTED = {
    "en": "Invalid sync tool selected.",
    "es": "Herramienta de sincronización inválida seleccionada.",
    "tr": "Geçersiz senkronizasyon aracı seçildi."
}
TEXT_SELECTED_FOLDER = {
    "en": "Selected folder: {}",
    "es": "Carpeta seleccionada: {}",
    "tr": "Seçilen klasör: {}"
}
TEXT_NO_FOLDER_SELECTED = {
    "en": "No folder selected.",
    "es": "No se seleccionó ninguna carpeta.",
    "tr": "Klasör seçilmedi."
}
TEXT_DESTINATION_FOLDER_DOES_NOT_EXIST = {
    "en": "The selected destination folder does not exist.",
    "es": "La carpeta de destino seleccionada no existe.",
    "tr": "Seçilen hedef klasör mevcut değil."
}
ADDED_PAIRS_MSG = {
    "en": "Added {} reference subtitle pair{}",
    "es": "Agregado {} par{} de subtítulos de referencia",
    "tr": "{} referans altyazı çifti eklendi"
}
SKIPPED_DUPLICATES_MSG = {
    "en": "Skipped {} duplicate pair{}",
    "es": "Omitido {} par{} duplicado{}",
    "tr": "{} yinelenen çift atlandı"
}
INVALID_PARENT_ITEM = {
    "en": "Invalid parent item with no values.",
    "es": "Elemento principal inválido sin valores.",
    "tr": "Değer içermeyen geçersiz üst öğe."
}
SKIP_NO_VIDEO_NO_SUBTITLE = {
    "en": "Skipping entry with no video and no subtitle.",
    "es": "Omitiendo entrada sin video ni subtítulo.",
    "tr": "Video ve altyazı olmayan girdi atlanıyor."
}
SKIP_NO_SUBTITLE = {
    "en": "Skipping '{video_file}': No subtitle file.",
    "es": "Omitiendo '{video_file}': No hay archivo de subtítulos.",
    "tr": "'{video_file}' atlanıyor: Altyazı dosyası yok."
}
SKIP_NO_VIDEO = {
    "en": "Skipping '{subtitle_file}': No video/reference file.",
    "es": "Omitiendo '{subtitle_file}': No hay archivo de video/referencia.",
    "tr": "'{subtitle_file}' atlanıyor: Video/referans dosyası yok."
}
SKIP_UNPAIRED_ITEM = {
    "en": "Unpaired item skipped.",
    "es": "Elemento no emparejado omitido.",
    "tr": "Eşleşmemiş öğe atlandı."
}
SKIPPING_ALREADY_SYNCED = {
    "en": "Skipping {filename}: Already synced.",
    "es": "Omitiendo {filename}: Ya sincronizado.",
    "tr": "{filename} atlanıyor: Zaten senkronize."
}
CONVERTING_SUBTITLE = {
    "en": "Converting {file_extension} to SRT...",
    "es": "Convirtiendo {file_extension} a SRT...",
    "tr": "{file_extension} uzantısı SRT'ye dönüştürülüyor..."
}
SYNCING_LOG_TEXT = {
    "en": "[{}/{}] Syncing {} with {}...\n",
    "es": "[{}/{}] Sincronizando {} con {}...\n",
    "tr": "[{}/{}] {} ile {} senkronize ediliyor...\n"
}
ERROR_CONVERTING_SUBTITLE = {
    "en": "Error converting subtitle: {error_message}",
    "es": "Error al convertir subtítulo: {error_message}",
    "tr": "Altyazı dönüştürme hatası: {error_message}"
}
SUBTITLE_CONVERTED = {
    "en": "Subtitle successfully converted and saved to: {srt_file}.",
    "es": "Subtítulo convertido exitosamente y guardado en: {srt_file}.",
    "tr": "Altyazı başarıyla dönüştürüldü ve kaydedildi: {srt_file}."
}
ERROR_UNSUPPORTED_CONVERSION = {
    "en": "Error: Conversion for {file_extension} is not supported.",
    "es": "Error: La conversión para {file_extension} no está soportada.",
    "tr": "Hata: {file_extension} dönüştürme desteklenmiyor."
}
FAILED_CONVERT_SUBTITLE = {
    "en": "Failed to convert subtitle file: {subtitle_file}",
    "es": "Error al convertir el archivo de subtítulos: {subtitle_file}",
    "tr": "Altyazı dosyası dönüştürülemedi: {subtitle_file}"
}
FAILED_CONVERT_VIDEO = {
    "en": "Failed to convert video/reference file: {video_file}",
    "es": "Error al convertir archivo de video/referencia: {video_file}",
    "tr": "Video/referans dosyası dönüştürülemedi: {video_file}"
}
SPLIT_PENALTY_ZERO = {
    "en": "Split penalty is set to 0. Using --no-split argument...",
    "es": "La penalización de división se establece en 0. Usando el argumento --no-split...",
    "tr": "Bölme cezası 0 olarak ayarlandı. --no-split argümanı kullanılıyor..."
}
SPLIT_PENALTY_SET = {
    "en": "Split penalty is set to {split_penalty}...",
    "es": "La penalización de división se establece en {split_penalty}...",
    "tr": "Bölme cezası {split_penalty} olarak ayarlandı..."
}
USING_REFERENCE_SUBTITLE = {
    "en": "Using reference subtitle for syncing...",
    "es": "Usando subtítulo de referencia para sincronizar...",
    "tr": "Senkronizasyon için referans altyazı kullanılıyor..."
}
USING_VIDEO_FOR_SYNC = {
    "en": "Using video for syncing...",
    "es": "Usando video para sincronizar...",
    "tr": "Senkronizasyon için video kullanılıyor..."
}
ENABLED_NO_FIX_FRAMERATE = {
    "en": "Enabled: Don't fix framerate.",
    "es": "Habilitado: No corregir la velocidad de fotogramas.",
    "tr": "Etkinleştirildi: Kare hızını düzeltme."
}
ENABLED_GSS = {
    "en": "Enabled: Golden-section search.",
    "es": "Habilitado: Búsqueda de sección áurea.",
    "tr": "Etkinleştirildi: Altın oran araması."
}
ENABLED_AUDITOK_VAD = {
    "en": "Enabled: Using auditok instead of WebRTC's VAD.",
    "es": "Habilitado: Usando auditok en lugar de VAD de WebRTC.",
    "tr": "Etkinleştirildi: WebRTC'nin VAD'si yerine auditok kullanılıyor."
}
ADDITIONAL_ARGS_ADDED = {
    "en": "Additional arguments: {additional_args}",
    "es": "Argumentos adicionales: {additional_args}",
    "tr": "Ek argümanlar: {additional_args}"
}
SYNCING_STARTED = {
    "en": "Syncing started:",
    "es": "Sincronización iniciada:",
    "tr": "Senkronizasyon başlatıldı:"
}
SYNCING_ENDED = {
    "en": "Syncing ended.",
    "es": "Sincronización finalizada.",
    "tr": "Senkronizasyon tamamlandı."
}
SYNC_SUCCESS = {
    "en": "Success! Synchronized subtitle saved to: {output_subtitle_file}\n\n",
    "es": "¡Éxito! Subtítulo sincronizado guardado en: {output_subtitle_file}\n\n",
    "tr": "Başarılı! Senkronize altyazı kaydedildi: {output_subtitle_file}\n\n"
}
SYNC_ERROR = {
    "en": "Error occurred during synchronization of {filename}",
    "es": "Ocurrió un error durante la sincronización de {filename}",
    "tr": "{filename} senkronizasyonu sırasında hata oluştu"
}
SYNC_ERROR_OCCURRED = {
    "en": "Error occurred during synchronization. Please check the log messages.",
    "es": "Ocurrió un error durante la sincronización. Por favor, revise los mensajes de registro.",
    "tr": "Senkronizasyon sırasında hata oluştu. Lütfen kayıt mesajlarını kontrol edin."
}
BATCH_SYNC_COMPLETED = {
    "en": "Batch syncing completed.",
    "es": "Sincronización por lotes completada.",
    "tr": "Toplu senkronizasyon tamamlandı."
}
PREPARING_SYNC = {
    "en": "Preparing {base_name}{file_extension} for automatic sync...",
    "es": "Preparando {base_name}{file_extension} para sincronización automática...",
    "tr": "Otomatik senkronizasyon için {base_name}{file_extension} hazırlanıyor..."
}
CONVERTING_TTML = {
    "en": "Converting TTML/DFXP/ITT to SRT...",
    "es": "Convirtiendo TTML/DFXP/ITT a SRT...",
    "tr": "TTML/DFXP/ITT uzantısı SRT'ye dönüştürülüyor..."
}
CONVERTING_VTT = {
    "en": "Converting VTT to SRT...",
    "es": "Convirtiendo VTT a SRT...",
    "tr": "VTT uzantısı SRT'ye dönüştürülüyor..."
}
CONVERTING_SBV = {
    "en": "Converting SBV to SRT...",
    "es": "Convirtiendo SBV a SRT...",
    "tr": "SBV uzantısı SRT'ye dönüştürülüyor..."
}
CONVERTING_SUB = {
    "en": "Converting SUB to SRT...",
    "es": "Convirtiendo SUB a SRT...",
    "tr": "SUB uzantısı SRT'ye dönüştürülüyor..."
}
CONVERTING_ASS = {
    "en": "Converting ASS/SSA to SRT...",
    "es": "Convirtiendo ASS/SSA a SRT...",
    "tr": "ASS/SSA uzantısı SRT'ye dönüştürülüyor..."
}
CONVERTING_STL = {
    "en": "Converting STL to SRT...",
    "es": "Convirtiendo STL a SRT...",
    "tr": "STL uzantısı SRT'ye dönüştürülüyor..."
}
CONVERSION_NOT_SUPPORTED = {
    "en": "Error: Conversion for {file_extension} is not supported.",
    "es": "Error: La conversión para {file_extension} no está soportada.",
    "tr": "Hata: {file_extension} dönüştürme desteklenmiyor."
}
RETRY_ENCODING_MSG = {
    "en": "Previous sync failed. Retrying with pre-detected encodings...",
    "es": "La sincronización anterior falló. Reintentando con codificaciones pre-detectadas...",
    "tr": "Önceki senkronizasyon başarısız oldu. Önceden tespit edilen kodlamalarla yeniden deneniyor..."
}
ALASS_SPEED_OPTIMIZATION_LOG = {
    "en": "Disabled: Speed optimization...",
    "es": "Deshabilitado: Optimización de velocidad...",
    "tr": "Devre dışı: Hız optimizasyonu..."
}
ALASS_DISABLE_FPS_GUESSING_LOG = {
    "en": "Disabled: FPS guessing...",
    "es": "Deshabilitado: Adivinación de FPS...",
    "tr": "Devre dışı: FPS tahmini..."
}
CHANGING_ENCODING_MSG = {
    "en": "Encoding of the synced subtitle does not match the original subtitle's encoding. Changing from {synced_subtitle_encoding} to {encoding_inc}...",
    "es": "La codificación del subtítulo sincronizado no coincide con la codificación del subtítulo original. Cambiando de {synced_subtitle_encoding} a {encoding_inc}...",
    "tr": "Senkronize altyazının kodlaması, orijinal altyazının kodlamasıyla eşleşmiyor. {synced_subtitle_encoding} kodlamasından {encoding_inc} kodlamasına geçiliyor..."
}
ENCODING_CHANGED_MSG = {
    "en": "Encoding changed successfully.",
    "es": "Codificación cambiada con éxito.",
    "tr": "Kodlama başarıyla değiştirildi."
}
SYNC_SUCCESS_COUNT = {
    "en": "Successfully synced {success_count} subtitle file(s).",
    "es": "Se sincronizaron correctamente {success_count} archivo(s) de subtítulos.",
    "tr": "{success_count} altyazı dosyası başarıyla senkronize edildi."
}
SYNC_FAILURE_COUNT = {
    "en": "Failed to sync {failure_count} subtitle file(s).",
    "es": "No se pudo sincronizar {failure_count} archivo(s) de subtítulos.",
    "tr": "{failure_count} altyazı dosyası senkronize edilemedi."
}
SYNC_FAILURE_COUNT_BATCH = {
    "en": "Failed to sync {failure_count} pair(s):",
    "es": "No se pudo sincronizar {failure_count} par(es):",
    "tr": "{failure_count} çift senkronize edilemedi:"
}
ERROR_CHANGING_ENCODING_MSG = {
    "en": "Error changing encoding: {error_message}\n",
    "es": "Error al cambiar la codificación: {error_message}\n",
    "tr": "Kodlama değiştirilirken hata: {error_message}\n"
}
BACKUP_CREATED = {
    "en": "A backup of the existing subtitle file has been saved to: {output_subtitle_file}.",
    "es": "Se ha guardado una copia de seguridad del archivo de subtítulos existente en: {output_subtitle_file}.",
    "tr": "Mevcut altyazı dosyasının bir yedeği kaydedildi: {output_subtitle_file}."
}
CHECKING_SUBTITLE_STREAMS = {
    "en": "Checking the video for subtitle streams...",
    "es": "Verificando el video para flujos de subtítulos...",
    "tr": "Videodaki altyazı akışları kontrol ediliyor..."
}
FOUND_COMPATIBLE_SUBTITLES = {
    "en": "Found {count} compatible subtitles to extract.\nExtracting subtitles to folder: {output_folder}...",
    "es": "Se encontraron {count} subtítulos compatibles para extraer.\nExtrayendo subtítulos en la carpeta: {output_folder}...",
    "tr": "Çıkartılacak {count} uyumlu altyazı bulundu.\nAltyazılar şu klasöre çıkartılıyor: {output_folder}..."
}
NO_COMPATIBLE_SUBTITLES = {
    "en": "No compatible subtitles found to extract.",
    "es": "No se encontraron subtítulos compatibles para extraer.",
    "tr": "Çıkartılacak uyumlu altyazı bulunamadı."
}
SUCCESSFULLY_EXTRACTED = {
    "en": "Successfully extracted: {filename}.",
    "es": "Extraído exitosamente: {filename}.",
    "tr": "Başarıyla çıkartıldı: {filename}."
}
CHOOSING_BEST_SUBTITLE = {
    "en": "Selecting the best subtitle for syncing...",
    "es": "Seleccionando el mejor subtítulo para sincronizar...",
    "tr": "Senkronizasyon için en iyi altyazı seçiliyor..."
}
CHOSEN_SUBTITLE = {
    "en": "Selected: {filename} with timestamp difference: {score}",
    "es": "Seleccionado: {filename} con diferencia de marca de tiempo: {score}",
    "tr": "Seçildi: {filename}, zaman damgası farkı: {score}"
}
FAILED_TO_EXTRACT_SUBTITLES = {
    "en": "Failed to extract subtitles. Error: {error}",
    "es": "No se pudieron extraer los subtítulos. Error: {error}",
    "tr": "Altyazılar çıkarılamadı. Hata: {error}"
}
USED_THE_LONGEST_SUBTITLE = {
    "en": "Used the longest subtitle file because parse_timestamps failed.",
    "es": "Se usó el archivo de subtítulos más largo porque parse_timestamps falló.",
    "tr": "parse_timestamps başarısız olduğu için en uzun altyazı dosyası kullanıldı."
}
DELETING_EXTRACTED_SUBTITLE_FOLDER = {
    "en": "Deleting the extracted subtitles folder...",
    "es": "Eliminando la carpeta de subtítulos extraídos...",
    "tr": "Çıkarılan altyazılar klasörü siliniyor..."
}
DELETING_CONVERTED_SUBTITLE = {
    "en": "Deleting the converted subtitle file...",
    "es": "Eliminando el archivo de subtítulos convertido...",
    "tr": "Dönüştürülmüş altyazı dosyası siliniyor..."
}
ADDED_FILES_TEXT = {
    "en": "Added {added_files} files",
    "es": "Agregado {added_files} archivos",
    "tr": "{added_files} dosya eklendi"
}
SKIPPED_DUPLICATE_FILES_TEXT = {
    "en": "Skipped {skipped_files} duplicate files",
    "es": "Omitido {skipped_files} archivos duplicados",
    "tr": "{skipped_files} yinelenen dosya atlandı"
}
SKIPPED_OTHER_LIST_FILES_TEXT = {
    "en": "Skipped {duplicate_in_other} files already in other list",
    "es": "Omitido {duplicate_in_other} archivos ya en la otra lista",
    "tr": "Diğer listede bulunan {duplicate_in_other} dosya atlandı"
}
SKIPPED_SEASON_EPISODE_DUPLICATES_TEXT = {
    "en": "Skipped {len} files with duplicate season/episode numbers",
    "es": "Omitido {len} archivos con números de temporada/episodio duplicados",
    "tr": "Aynı sezon/bölüm numaralarına sahip {len} dosya atlandı"
}
SKIPPED_INVALID_FORMAT_FILES_TEXT = {
    "en": "Skipped {len} files without valid episode format",
    "es": "Omitido {len} archivos sin formato de episodio válido",
    "tr": "Geçerli bölüm formatı olmayan {len} dosya atlandı"
}
NO_FILES_SELECTED = {
    "en": "No files selected.",
    "es": "No se seleccionaron archivos.",
    "tr": "Dosya seçilmedi."
}
NO_ITEM_SELECTED_TO_REMOVE = {
    "en": "No item selected to remove.",
    "es": "No se seleccionó ningún elemento para eliminar.",
    "tr": "Kaldırmak için öğe seçilmedi."
}
NO_FILES_SELECTED_TO_SHOW_PATH = {
    "en": "No file selected to show path.",
    "es": "No se seleccionó ningún archivo para mostrar la ruta.",
    "tr": "Yolu göstermek için dosya seçilmedi."
}
REMOVED_ITEM = {
    "en": "Removed item.",
    "es": "Elemento eliminado.",
    "tr": "Öğe kaldırıldı."
}
FILES_MUST_CONTAIN_PATTERNS = {
    "en": "Files must contain patterns like S01E01, 1x01 etc.",
    "es": "Los archivos deben contener patrones como S01E01, 1x01 etc.",
    "tr": "Dosyalar S01E01, 1x01 vb. kalıplar içermelidir."
}
NO_VALID_SUBTITLE_FILES = {
    "en": "No valid subtitle files found.",
    "es": "No se encontraron archivos de subtítulos válidos.",
    "tr": "Geçerli altyazı dosyası bulunamadı."
}
NO_SUBTITLE_PAIRS_TO_PROCESS = {
    "en": "No subtitle pairs to process.",
    "es": "No hay pares de subtítulos para procesar.",
    "tr": "İşlenecek altyazı çifti yok."
}
NO_MATCHING_SUBTITLE_PAIRS_FOUND = {
    "en": "No matching subtitle pairs found.",
    "es": "No se encontraron pares de subtítulos coincidentes.",
    "tr": "Eşleşen altyazı çifti bulunamadı."
}
NO_VALID_SUBTITLE_PAIRS_TO_PROCESS = {
    "en": "No valid subtitle pairs to process.",
    "es": "No hay pares de subtítulos válidos para procesar.",
    "tr": "İşlenecek geçerli altyazı çifti yok."
}