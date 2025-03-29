/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
import{util as e}from"../sw_modules/util.js";import{Proxy as E}from"../sw_modules/proxy.js";import{SETTINGS as r}from"../sw_modules/settings.js";import{dcLocalStorage as t}from"./local-storage.js";import{privateApi as _}from"../sw_modules/private-api.js";import{loggingApi as o}from"./loggingApi.js";import{getActiveExperimentAnalyticsString as s}from"../sw_modules/express.js";let C=!0;const i=new function(){E&&(this.proxy=E.proxy.bind(this)),this.e={EXTENSION_INSTALLED:"DCBrowserExt:Extension:Installed:Op",EXTENSION_INSTALLED_NEW:"DCBrowserExt:Extension:Installed:New:Op",EXTENSION_INSTALLED_DIRECT:"DCBrowserExt:Extension:Installed:Direct:Op",EXTENSION_INSTALLED_DEVELOPMENT:"DCBrowserExt:Extension:Installed:Development:Op",EXTENSION_INSTALLED_ADMIN:"DCBrowserExt:Extension:Installed:Admin:Op",EXTENSION_INSTALLED_SIDE_LOADED:"DCBrowserExt:Extension:Installed:Side:Loaded:Op",EXTENSION_INSTALLED_OTHER:"DCBrowserExt:Extension:Installed:Other:Op",EXTENSION_INSTALLED_SOURCE:"DCBrowserExt:Extension:Installed:Direct:SOURCE:Op",EXTENSION_INSTALLED_SIDE_LOADED_SOURCE:"DCBrowserExt:Extension:Installed:Side:Loaded:SOURCE:Op",EXTENSION_INSTALLED_SIDE_LOADED_MONTH_YEAR:"DCBrowserExt:Extension:Installed:Side:Loaded:M:MONTH:Y:YEAR:Op",EXTENSION_INSTALLED_UPSELL:"DCBrowserExt:Extension:Installed:Upsell:Op",EXTENSION_INSTALLED_DEFAULT:"DCBrowserExt:Extension:Installed:Unknown:Op",EXTENSION_REPROMPT_TRACKING:"DCBrowserExt:Reprompt:Reason:REASON:Type:TYPE",EXTENSION_UPDATE:"DCBrowserExt:Extension:Update:Op",EXTENSION_STARTUP:"DCBrowserExt:Extension:Startup:Op",EXTENSION_FORCE_UNINSTALL:"DCBrowserExt:Extension:ForceUninstall:Op",SIGN_IN_SHOWN:"DCBrowserExt:SignIn:OPERATION:Shown",SIGN_IN_COMPLETE:"DCBrowserExt:SignIn:OPERATION:Complete:Op",SIGN_IN_ABANDONED:"DCBrowserExt:SignIn:Abandoned:Op",SIGN_OUT_CLICKED:"DCBrowserExt:SignOut:Clicked",FLICKR_OFFER_SHOWN:"DCBrowserExt:Flickr:Offer:Shown",FLICKR_OFFER_CLICKED:"DCBrowserExt:Flickr:Offer:Clicked",FLICKR_CONTEXT_CLICK:"DCBrowserExt:Flickr:Context:Clicked",CONTEXT_UPLOAD_PDF_PAGE:"DCBrowserExt:Context:Upload:PdfPage:Clicked",CONTEXT_UPLOAD_LINK:"DCBrowserExt:Context:Upload:Link:Clicked",CONTEXT_UPLOAD_IMAGE:"DCBrowserExt:Context:Upload:Image:Clicked",CONTEXT_MENU_CONVERT_PAGE:"DCBrowserExt:ContextMenu:ConvertPage:Clicked",CONTEXT_MENU_CONVERT_LINK:"DCBrowserExt:ContextMenu:ConvertLink:Clicked",CONTEXT_MENU_EXPRESS_VERB:"DCBrowserExt:ContextMenu:Express:TARGET:VERB:Clicked",CONTEXT_MENU_APPEND_PAGE:"DCBrowserExt:ContextMenu:AppendPage:Clicked",CONTEXT_MENU_APPEND_LINK:"DCBrowserExt:ContextMenu:AppendLink:Clicked",REDIRECT:"DCBrowserExt:Redirect:OPERATION:Op",PDF_MENU_UPLOAD_COMPLETE_SHOWN:"DCBrowserExt:PDF:Menu:OPERATION:Upload:Complete:Shown",PDF_SOURCE_SIZE:"DCBrowserExt:PDF:Source:Size:RANGE:Op",TREFOIL_CLICKED:"DCBrowserExt:Trefoil:Clicked",TREFOIL_ACROBAT_LABEL_CLICKED:"DCBrowserExt:TrefoilMenu:AcrobatLabel:Clicked",TREFOIL_PDF_MENU_SHOWN:"DCBrowserExt:TrefoilMenu:PDF:Popup:Shown",TREFOIL_PDF_FROM_CLICK:"DCBrowserExt:TrefoilMenu:PDF:FromClick:TIREKICK:Shown",TREFOIL_PDF_VISIT_AIC:"DCBrowserExt:TrefoilMenu:PDF:VisitAIC:TIREKICK:Clicked",TREFOIL_PDF_ACROBAT:"DCBrowserExt:TrefoilMenu:PDF:OpenInAcrobat:TIREKICK:Clicked",TREFOIL_PDF_READER:"DCBrowserExt:TrefoilMenu:PDF:OpenInReader:TIREKICK:Clicked",TREFOIL_PDF_DOWNLOAD_OPENED:"DCBrowserExt:TrefoilMenu:PDF:OpenInAcrobat:Complete:Op",TREFOIL_PDF_DOWNLOAD_OPENED_READER:"DCBrowserExt:TrefoilMenu:PDF:OpenInReader:Complete:Op",TREFOIL_PDF_DOWNLOAD_OPEN_FAILED:"DCBrowserExt:TrefoilMenu:PDF:OpenInAcrobat:Failed:Op",TREFOIL_PDF_DOWNLOAD_OPEN_FAILED_READER:"DCBrowserExt:TrefoilMenu:PDF:OpenInReader:Failed:Op",TREFOIL_HTML_FROM_CLICK:"DCBrowserExt:TrefoilMenu:HTML:FromClick:Shown",TREFOIL_HTML_OPTIONS_FROM_CLICK:"DCBrowserExt:TrefoilMenu:HTML:WithOptions:FromClick:Shown",TREFOIL_HTML_VISIT_AIC:"DCBrowserExt:TrefoilMenu:HTML:VisitAIC:TIREKICK:Clicked",TREFOIL_HTML_PREFERENCES_CLICK:"DCBrowserExt:TrefoilMenu:HTML:Preferences:Clicked",TREFOIL_HTML_CONVERT_NEW:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:New:TIREKICK:Clicked",TREFOIL_HTML_CONVERT_APPEND:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:Append:TIREKICK:Clicked",TREFOIL_HTML_CONVERT_NO_OPEN:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:NoOpen:Clicked",TREFOIL_HTML_CONVERT_OPEN_DEFAULT:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:WithOpen:Default:Clicked",TREFOIL_HTML_CONVERT_OPEN_CHANGED:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:WithOpen:Changed:Clicked",TREFOIL_HTML_CONVERT_WAITING:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:Waiting:Shown",TREFOIL_HTML_CONVERT_DOWNLOADING:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:Downloading:Shown",TREFOIL_HTML_CONVERT_IN_PROGRESS:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:InProgress:Shown",TREFOIL_HTML_CONVERT_CANCELLED:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:Cancelled:Shown",TREFOIL_HTML_CONVERT_COMPLETE:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:Complete:Shown",TREFOIL_HTML_CONVERT_FAILED:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:Failed:Shown",TREFOIL_HTML_CONVERT_FAILED_JS:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:FailedJS:Shown",TREFOIL_HTML_CONVERT_FAILED_DOM:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:FailedDOM:Shown",TREFOIL_HTML_CONVERT_FAILED_HOST:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:FailedHOST:Shown",TREFOIL_HTML_CONVERT_FAILED_TRY:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:FailedTRY:Shown",TREFOIL_HTML_CONVERT_NO_ACROBAT:"DCBrowserExt:TrefoilMenu:HTML:ConvertHTML:NoAcrobat:Shown",TREFOIL_HTML_OPENPDF_PREF_ON:"DCBrowserExt:TrefoilMenu:HTML:OpenPDFPref:On:Clicked",TREFOIL_HTML_OPENPDF_PREF_OFF:"DCBrowserExt:TrefoilMenu:HTML:OpenPDFPref:Off:Clicked",PERSIST_PDF_MENU_SHOWN:"DCBrowserExt:PersistMenu:PDF:Popup:Shown",PERSIST_PDF_ACROBAT:"DCBrowserExt:PersistMenu:PDF:OpenInAcrobat:TIREKICK:Clicked",PERSIST_PDF_DOWNLOAD_OPENED:"DCBrowserExt:PersistMenu:PDF:OpenInAcrobat:Complete:Op",PERSIST_PDF_DOWNLOAD_OPEN_FAILED:"DCBrowserExt:PersistMenu:PDF:OpenInAcrobat:Failed:Op",PERSIST_PDF_MENU_CLOSED:"DCBrowserExt:PersistMenu:PDF:Close:TIREKICK:Clicked",PERSIST_PDF_OPENPDF_PREF_OFF:"DCBrowserExt:PersistMenu:PDF:OpenPDFPref:Off:Clicked",PERSIST_PDF_READER:"DCBrowserExt:PersistMenu:PDF:OpenInReader:TIREKICK:Clicked",PERSIST_PDF_DOWNLOAD_OPENED_READER:"DCBrowserExt:PersistMenu:PDF:OpenInReader:Complete:Op",PERSIST_PDF_DOWNLOAD_OPEN_FAILED_READER:"DCBrowserExt:PersistMenu:PDF:OpenInReader:Failed:Op",PERSIST_PDF_MENU_CLOSED_READER:"DCBrowserExt:PersistMenu:PDF:CloseReader:TIREKICK:Clicked",PERSIST_PDF_OPENPDF_PREF_OFF_READER:"DCBrowserExt:PersistMenu:PDF:OpenPDFPrefReader:Off:Clicked",UPLOAD_PROGRESS_SHOWN:"DCBrowserExt:Upload:OPERATION:Progress:Shown",CREATE_FORM_PROGRESS_SHOWN:"DCBrowserExt:Upload:FillSign:CreateForm:Progress:Shown",UPLOAD_COMPLETE:"DCBrowserExt:Upload:OPERATION:Complete:Op",CREATE_FORM_COMPLETE:"DCBrowserExt:Upload:FillSign:CreateForm:Complete:Op",UPLOAD_RENAME_CLICKED:"DCBrowserExt:Upload:RenameOrMove:Clicked",ERROR_SHOWN:"DCBrowserExt:Error:Shown",ERROR_WRONG_MIME_TYPE:"DCBrowserExt:Error:WrongMimeType:Shown",OPTIONS_SET_ENV:"DCBrowserExt:Options:SetEnv:ENVIRONMENT:Op",OPTIONS_ENABLE_HTML2PDF:"DCBrowserExt:Options:EnableHTML2PDF:ENVIRONMENT:Op",HTML_SOURCE_SIZE:"DCBrowserExt:HTML:Source:Size:RANGE:Op",HTML_SOURCE_SIZE_TOO_LARGE_ERROR:"DCBrowserExt:HTML:Source:Size:TooLarge:Error:Shown",HTML_SOURCE_SITE:"DCBrowserExt:HTML:Source:Site:SITE",HTML_SOURCE_PROTOCOL:"DCBrowserExt:HTML:Source:Protocol:PROTOCOL",HTML_SOURCE_CONTENT:"DCBrowserExt:HTML:Source:CONTENT:Op",HTML_CONVERSION_STAGE_TIMING:"DCBrowserExt:HTML:Conversion:STAGE:TIMING",OPTIONS_PAGE:"DCBrowserExt:OptionsPage:Shown",PERSIST_PDF_READER_FS:"DCBrowserExt:PersistMenu:PDF:OpenInReader:Clicked:FillnSign",PERSIST_PDF_ACROBAT_FS:"DCBrowserExt:PersistMenu:PDF:OpenInAcrobat:Clicked:FillnSign",PDF_FORM_DETECTED_READER:"DCBrowserExt:PDF:Reader:Form",PDF_FORM_DETECTED_ACROBAT:"DCBrowserExt:PDF:Acrobat:Form",TREFOIL_PDF_READER_FS:"DCBrowserExt:TrefoilMenu:PDF:OpenInReader:Clicked:FillnSign",TREFOIL_PDF_ACROBAT_FS:"DCBrowserExt:TrefoilMenu:PDF:OpenInAcrobat:Clicked:FillnSign",PERSIST_PDF_MENU_CLOSED_READER_FS:"DCBrowserExt:PersistMenu:PDF:CloseReader:Clicked:FillnSign",PERSIST_PDF_MENU_CLOSED_ACROBAT_FS:"DCBrowserExt:PersistMenu:PDF:CloseAcrobat:Clicked:FillnSign",WELCOME_PDF_TAB_CLOSED:"DCBrowserExt:Welcome:PDF:TabClosed",SIGN_IN_PROMPT_TAB_CLOSED:"DCBrowserExt:SignInPrompt:PDF:TabClosed",FRICTIONLESS_WIDGET_LOADED:"DCBrowserExt:WORKFLOW:TOOL:Widget:Loaded",FRICTIONLESS_WIDGET_LOADING_FAILED:"DCBrowserExt:TOOL:Widget:Failed",FRICTIONLESS_WIDGET_STARTUP_ERROR:"DCBrowserExt:TOOL:Widget:StartupError",FRICTIONLESS_HOME_SCREEN_SHOWN:"DCBrowserExt:Widget:Home:Shown",FRICTIONLESS_TOOL_SELECTED:"DCBrowserExt:Widget:TOOL:Clicked",FRICTIONLESS_FILE_UPLOAD_STARTED:"DCBrowserExt:Widget:File:Upload:Started",FRICTIONLESS_FILE_UPLOAD_COMPLETED:"DCBrowserExt:Widget:File:Upload:Completed",FRICTIONLESS_AUTO_SUGGESTION_DISABLED:"DCBrowserExt:Widget:AutoSuggestion:Disabled",FRICTIONLESS_AUTO_SUGGESTION_ENABLED:"DCBrowserExt:Widget:AutoSuggestion:Enabled",ACROBAT_ONLINE_CLICKED:"DCBrowserExt:Widget:AcrobatOnline:Clicked",FRICTIONLESS_INFO_MESSAGE_SHOWN:"DCBrowserExt:Widget:Info:Shown",FRICTIONLESS_INFO_SETTINGS_CLICKED:"DCBrowserExt:Widget:Info:Settings:Clicked",FRICTIONLESS_WIDGET_CROSS_CLICKED:"DCBrowserExt:Widget:Cross:Clicked",FRICTIONLESS_WIDGET_CLOSED:"DCBrowserExt:Widget:Closed",FRICTIONLESS_TOOL_SELECTED_EDIT_REORDER:"DCBrowserExt:Widget:ReorderPages:Clicked",FRICTIONLESS_TOOL_SELECTED_EDIT_ROTATE:"DCBrowserExt:Widget:RotatePages:Clicked",FRICTIONLESS_TOOL_SELECTED_EDIT_DELETE:"DCBrowserExt:Widget:DeletePages:Clicked",FRICTIONLESS_TOOL_SELECTED_FILL_SIGN:"DCBrowserExt:Widget:Fill&Sign:Clicked",FRICTIONLESS_TOOL_SELECTED_REQUEST_SIGNATURES:"DCBrowserExt:Widget:RequestSignatures:Clicked",FRICTIONLESS_TOOL_SELECTED_PDFTOWORD:"DCBrowserExt:Widget:PDFtoWORD:Clicked",FRICTIONLESS_TOOL_SELECTED_PDFTOJPG:"DCBrowserExt:Widget:PDFtoJPG:Clicked",FRICTIONLESS_TOOL_SELECTED_PDFTOEXCEL:"DCBrowserExt:Widget:PDFtoEXCEL:Clicked",FRICTIONLESS_TOOL_SELECTED_PDFTOPPT:"DCBrowserExt:Widget:PDFtoPPT:Clicked",FRICTIONLESS_TOOL_SELECTED_CONVERT_PDF:"DCBrowserExt:Widget:ConvertPDF:Clicked",FRICTIONLESS_TOOL_SELECTED_COMPRESS_PDF:"DCBrowserExt:Widget:CompressPDF:Clicked",FRICTIONLESS_CONVERSION_LIMITS:"DCBrowserExt:FLMsg:WORKFLOW:Limits:RESULT",FRICTIONLESS_USER_SIGNEDIN:"DCBrowserExt:FLMsg:WORKFLOW:SignInStatus:RESULT",FRICTIONLESS_SWITCH_TAB:"DCBrowserExt:FLMsg:WORKFLOW:SwitchTab",GOOGLE_URL_DECODE_ERROR:"DCBrowserExt:GQUERYANALYZER:DecodeUrlError",GOOGLE_SEARCHTERM_FETCH_ERROR:"DCBrowserExt:GQUERYANALYZER:SearchTermsFetchFailed",GOOGLE_SEARCHTERM_FOUND_MATCH:"DCBrowserExt:GQUERYANALYZER:SearchTermFoundMatch",PERSIST_PDF_ACROBAT_SHAREPOINT:"DCBrowserExt:PersistMenu:SharePointPDF:OpenInAcrobat:TIREKICK:Clicked",PERSIST_PDF_READER_SHAREPOINT:"DCBrowserExt:PersistMenu:SharePointPDF:OpenInReader:TIREKICK:Clicked",TREFOIL_PDF_ACROBAT_SHAREPOINT:"DCBrowserExt:TrefoilMenu:SharePointPDF:OpenInAcrobat:TIREKICK:Clicked",TREFOIL_PDF_READER_SHAREPOINT:"DCBrowserExt:TrefoilMenu:SharePointPDF:OpenInReader:TIREKICK:Clicked",PERSIST_FILLSIGN_ACROBAT_SHAREPOINT:"DCBrowserExt:PersistMenu:SharePointPDF:OpenInAcrobat:TIREKICK:Clicked:FillnSign",PERSIST_FILLSIGN_READER_SHAREPOINT:"DCBrowserExt:PersistMenu:SharePointPDF:OpenInReader:TIREKICK:Clicked:FillnSign",TREFOIL_FILLSIGN_ACROBAT_SHAREPOINT:"DCBrowserExt:TrefoilMenu:SharePointPDF:OpenInAcrobat:TIREKICK:Clicked:FillnSign",TREFOIL_FILLSIGN_READER_SHAREPOINT:"DCBrowserExt:TrefoilMenu:SharePointPDF:OpenInReader:TIREKICK:Clicked:FillnSign",VIEWER_FTE_OPEN_HELPX_ENABLED:"DCBrowserExt:Viewer:FTE:OpenHelpx:Enabled",VIEWER_FTE_OPEN_HELPX_DISABLED:"DCBrowserExt:Viewer:FTE:OpenHelpx:Disabled",PERSIST_PDF_MENU_FTE_SHOWN:"DCBrowserExt:Viewer:PersistMenu:PDF:OwnershipCard:LAUNCH:Shown",PERSIST_PDF_MENU_DMB_FTE_SHOWN:"DCBrowserExt:Viewer:PersistMenu:PDF:DMB:LAUNCH:Shown",PERSIST_PDF_MENU_RED_CARD_FTE_SHOWN:"DCBrowserExt:Viewer:PersistMenu:PDF:Red:Card:LAUNCH:Shown",PERSIST_PDF_MENU_FTE_DENIED:"DCBrowserExt:Viewer:PersistMenu:PDF:OwnershipCard:NoThanks:Clicked",PERSIST_PDF_MENU_FTE_CANCEL:"DCBrowserExt:Viewer:PersistMenu:PDF:OwnershipCard:NotNow:Clicked",PERSIST_PDF_MENU_FTE_ACCEPTED:"DCBrowserExt:Viewer:PersistMenu:PDF:OwnershipCard:REPROMPT:SetAsDefault:Clicked",PERSIST_PDF_MENU_DMB_CANCEL:"DCBrowserExt:Viewer:PersistMenu:PDF:DMB:REPROMPT:Cancel:Clicked",PERSIST_PDF_MENU_DMB_CONFIRM:"DCBrowserExt:Viewer:PersistMenu:PDF:DMB:REPROMPT:SetAsDef:Clicked",PERSIST_PDF_MENU_RED_CARD_CANCEL:"DCBrowserExt:Viewer:PersistMenu:PDF:Red:Card:REPROMPT:Cancel:Clicked",PERSIST_PDF_MENU_RED_CARD_CONFIRM:"DCBrowserExt:Viewer:PersistMenu:PDF:Red:Card:REPROMPT:SetAsDef:Clicked",PERSIST_PDF_MENU_FTE_REPROMPT_DENIED:"DCBrowserExt:Viewer:PersistMenu:PDF:OwnershipCard:Reprompt:NoThanks:Clicked",USE_ACROBAT_VIEWER_DISABLED_DEFAULT_OWNERSHIP:"DCBrowserExt:Viewer:Disabled:Ownership:Upgrade:SOURCE",USE_ACROBAT_VIEWER_DISABLED_DEFAULT_OWNERSHIP_EXPERIMENT:"DCBrowserExt:Viewer:Disabled:Ownership:Upgrade:SOURCE:EXPERIMENT",USE_ACROBAT_IN_CHROME_DISABLED:"DCBrowserExt:Viewer:Widget:UseAcrobatInChrome:Disabled",USE_ACROBAT_IN_CHROME_ENABLED:"DCBrowserExt:Viewer:Widget:UseAcrobatInChrome:Enabled",USE_ACROBAT_IN_EDGE_DISABLED:"DCBrowserExt:Viewer:Widget:UseAcrobatInEdge:Disabled",USE_ACROBAT_IN_EDGE_ENABLED:"DCBrowserExt:Viewer:Widget:UseAcrobatInEdge:Enabled",USE_ACROBAT_IN_EDGE_AUTO_ENABLED:"DCBrowserExt:Viewer:UseAcrobatInEdge:Auto:Enabled",USE_ACROBAT_IN_CHROME_AUTO_ENABLED:"DCBrowserExt:Viewer:UseAcrobatInChrome:Auto:Enabled",USE_ACROBAT_IN_EDGE_AUTO_ENABLED_ON_UPDATE:"DCBrowserExt:Viewer:UseAcrobatInEdge:Auto:Enabled:OnUpdate",USE_ACROBAT_IN_CHROME_AUTO_ENABLED_ON_UPDATE:"DCBrowserExt:Viewer:UseAcrobatInChrome:Auto:Enabled:OnUpdate",USE_ACROBAT_IN_EDGE_AUTO_ENABLED_ON_UPDATE_SOURCE:"DCBrowserExt:Viewer:UseAcrobatInEdge:Auto:Enabled:OnUpdate:SOURCE",USE_ACROBAT_IN_CHROME_AUTO_ENABLED_ON_UPDATE_SOURCE:"DCBrowserExt:Viewer:UseAcrobatInChrome:Auto:Enabled:OnUpdate:SOURCE",VIEWER_PDF_OPENED_MIME_HANDLER:"DCBrowserExt:Viewer:PDFOpenedinMimeViewer",VIEWER_EXTN_PDF_OPENED:"DCBrowserExt:Viewer:ExtnViewerPdfOpened",VIEWER_EXTN_PDF_OPENED_SOURCE:"DCBrowserExt:Viewer:ExtnViewerPdfOpened:SOURCE",VIEWER_PDF_PROCESS_OS_CD:"DCBrowserExt:Viewer:Status:Processing:OctetStream:ContentDisposition",VIEWER_PDF_PROCESS_OS_URL:"DCBrowserExt:Viewer:Status:Processing:OctetStream:URL",VIEWER_PDF_LOCAL_FILE:"DCBrowserExt:Viewer:Processing:LocalPDFFile",VIEWER_PDF_LOCAL_FILE_MIME_HANDLER:"DCBrowserExt:Viewer:Processing:LocalPDFFile:MimeHandler",VIEWER_PDF_LOCAL_FILE_IGNORED:"DCBrowserExt:Viewer:Ignoring:LocalPDFFile",VIEWER_PDF_DETECT_EMBED_PDF:"DCBrowserExt:Viewer:Detected:EmbededPDF",VIEWER_PDF_DETECT_EMBED_PDF_OCTET_CD:"DCBrowserExt:Viewer:Detected:EmbededPDF:ContentDisposition",VIEWER_PDF_DETECT_EMBED_PDF_OCTET_URL:"DCBrowserExt:Viewer:Detected:EmbededPDF:URL",VIEWER_PDF_DETECT_EMBED_PDF_TYPE_PDF:"DCBrowserExt:Viewer:Detected:EmbededPDF:ContentType",VIEWER_PDF_DETECT_EMBED_PDF:"DCBrowserExt:Viewer:Detected:EmbededPDF",VIEWER_PDF_WEBPAGE_OPENED:"DCBrowserExt:Detected:Webpage:Opened",VIEWER_KILL_SWITCH_TURNED_ON:"DCBrowserExt:Viewer:KillSwitch:Turned:On",VIEWER_KILL_SWITCH_OFF_SUCCESS:"DCBrowserExt:KillSwitch:Turned:Off",VIEWER_KILL_SWITCH_OFF_FAILED:"DCBrowserExt:KillSwitch:Failed:Off",LOCAL_STORAGE_DISABLED:"DCBrowserExt:Viewer:LocalStorgae:Disabled",VIEWER_FILLSIGN_CLICKED:"DCBrowserExt:Viewer:Reader:FillSign:Clicked",VIEWER_FILLSIGN_CLICKED_COMPLETE:"DCBrowserExt:Viewer:Reader:FillSign:Complete:Op",VIEWER_FILLSIGN_CLICKED_FAILED:"DCBrowserExt:Viewer:Reader:FillSign:Failed:Op",VIEWER_OPEN_IN_ACRO_CLICKED:"DCBrowserExt:Viewer:Reader:OpenInAcrobat:Clicked",VIEWER_OPEN_IN_ACRO_CLICKED_COMPLETE:"DCBrowserExt:Viewer:Reader:OpenInAcrobat:Complete:Op",VIEWER_OPEN_IN_ACRO_CLICKED_FAILED:"DCBrowserExt:Viewer:Reader:OpenInAcrobat:Failed:Op",VIEWER_SHAREPOINT_CLICKED:"DCBrowserExt:Viewer:Reader:Sharepoint:Clicked",VIEWER_SHAREPOINT_CLICKED_COMPLETE:"DCBrowserExt:Viewer:Reader:Sharepoint:Complete:Op",VIEWER_SHAREPOINT_FILLSIGN_CLICKED:"DCBrowserExt:Viewer:Reader:Sharepoint:FillSign:Clicked",VIEWER_SHAREPOINT_FILLSIGN_CLICKED_COMPLETE:"DCBrowserExt:Viewer:Reader:Sharepoint:FillSign:Complete:Op",VIEWER_IMS_SIGN_IN:"DCBrowserExt:Viewer:Ims:Sign:In",VIEWER_IMS_SIGN_OUT:"DCBrowserExt:Viewer:Ims:Sign:Out",VIEWER_ENABLED_PDF_OPEN_NATIVE_VIEWER:"DCBrowserExt:Viewer:ViewerEnabled:PdfOpen:NativeViewer",VIEWER_FALLBACK_TO_NATIVE_CDN_FORBIDDEN:"DCBrowserExt:Viewer:Error:FallbackToNative:Cdn:Forbidden",VIEWER_FALLBACK_TO_NATIVE_CDN_OFFLINE:"DCBrowserExt:Viewer:Error:FallbackToNative:Cdn:Offline",VIEWER_FALLBACK_TO_NATIVE_INCOGNITO:"DCBrowserExt:Viewer:Status:Ignored:Incognito:PDF",VIEWER_DISABLED_PDF_OPEN_NATIVE_VIEWER:"DCBrowserExt:Viewer:ViewerDisabled:APPLICATION:PdfOpen:NativeViewer",TREFOIL_SETTINGS_ICON_CLICKED:"DCBrowserExt:TrefoilMenu:Settings:Clicked",TREFOIL_SETTINGS_FAILED_TO_OPEN:"DCBrowserExt:TrefoilMenu:Settings:FailedToOpen",OPTIONS_ENABLED_ANALYTICS:"DCBrowserExt:Options:Analytics:Enabled",OPTIONS_DISABLED_ANALYTICS:"DCBrowserExt:Options:Analytics:Disabled",OPTIONS_ENABLED_OPEN_IN_ACROBAT:"DCBrowserExt:Options:OpenInAcrobat:Enabled",OPTIONS_DISABLED_OPEN_IN_ACROBAT:"DCBrowserExt:Options:OpenInAcrobat:Disabled",OPTIONS_ABOUT_ADOBE_ACROBAT_CLICKED:"DCBrowserExt:Options:AboutAdobeAcrobat:Clicked",OPTIONS_APPEARENCE_THEME_CHANGED:"DCBrowserExt:Options:theme:changed:OLDTHEME:to:NEWTHEME",OPTIONS_ENABLE_GENAI_FEATURES:"DCBrowserExt:Options:GenAIFeatures:Enabled",OPTIONS_DISABLE_GENAI_FEATURES:"DCBrowserExt:Options:GenAIFeatures:Disabled",OPTIONS_ACROBAT_GSUITE_TOUCHPOINT_ENABLED:"DCBrowserExt:Options:AcrobatGsuiteTouchpoint:Enabled",OPTIONS_ACROBAT_GSUITE_TOUCHPOINT_DISABLED:"DCBrowserExt:Options:AcrobatGsuiteTouchpoint:Disabled",OPTIONS_EXPRESS_TOUCHPOINT_ENABLED:"DCBrowserExt:Options:ExpressTouchpoint:Enabled",OPTIONS_EXPRESS_TOUCHPOINT_DISABLED:"DCBrowserExt:Options:ExpressTouchpoint:Disabled",OPTIONS_ENABLE_AI_MARKERS:"DCBrowserExt:Options:AIMarkers:Enabled",OPTIONS_DISABLE_AI_MARKERS:"DCBrowserExt:Options:AIMarkers:Disabled",UNINSTALL_DIALOG_UNINSTALLED_SUCCESSFUL:"DCBrowserExt:UninstallDialog:Uninstalled:Successful",UNINSTALL_USER_STATE_PENDING:"DCBrowserExt:Token:Null:State:Pending",UNINSTALL_USER_STATE:"DCBrowserExt:Token:Present:isPaidUser:ISPAID:shouldUninstall:VALUE",UNINSTALL_USER_STATE_FROM_VIEWER:"DCBrowserExt:SubsFromViewer:isPaidUser:ISPAID:shouldUninstall:VALUE",LOCAL_STORAGE_MIGRATION_SUCCESS:"DCBrowserExt:LSMigration:NoPreMV3:Successful",LOCAL_STORAGE_MIGRATION_FAILED:"DCBrowserExt:LSMigration:NoPreMV3:Failed",LOCAL_STORAGE_MIGRATION_RETRYING:"DCBrowserExt:LSMigration:NoPreMV3:Retrying",LOCAL_STORAGE_MIGRATION_RETRYING_SUCCESS:"DCBrowserExt:LSMigration:NoPreMV3:SuccessfulOnRetrying",WELCOME_PDF_LOADED:"DCBrowserExt:Viewer:Welcome:PDF:Loaded",STALE_USER_ADOBE_YOLO:"DCBrowserExt:AdobeYolo:StaleUserFound:SOURCE",USER_SIGNED_OUT_ADOBE_YOLO:"DCBrowserExt:AdobeYolo:UserSignedOut:SOURCE",SANITY_FAILED_ADOBE_YOLO:"DCBrowserExt:AdobeYolo:SanityFailed:SOURCE:VERSION:op",ADOBE_YOLO_JUMP_ERROR:"DCBrowserExt:AdobeYolo:JumpError:SOURCE",ADOBE_YOLO_JUMP_SUCCESS:"DCBrowserExt:AdobeYolo:JumpSuccess:SOURCE",ADOBE_YOLO_JUMP_FREEZE:"DCBrowserExt:AdobeYolo:JumpFreeze:SOURCE",ADOBE_YOLO_JUMP_ERROR_REASON:"DCBrowserExt:AdobeYolo:Error:REASON:SOURCE:VERSION:op",ADOBE_YOLO_JUMP_INITIATED:"DCBrowserExt:AdobeYolo:JumpInitiated:SOURCE",ADOBE_YOLO_ERROR_PM_OFF:"DCBrowserExt:AdobeYolo:UserInfo:ProtectedModeOff",ADOBE_YOLO_ERROR_LICENSENOTINITIALISED:"DCBrowserExt:AdobeYolo:UserInfo:LicenseNotInitialised",ADOBE_YOLO_ERROR_EMPTYACCESSTOKEN:"DCBrowserExt:AdobeYolo:UserInfo:EmptyAccessToken",SAVE_LOCATION_PREFERENCE_CHANGED:"DCBrowserExt:Options:SaveLocation:changed:OLDPREF:to:NEWPREF",LOCAL_FTE_DISPLAYED:"DCBrowserExt:LocalFte:Displayed:Successful:VARIANT",LOCAL_FTE_GO_TO_SETTINGS_CLICKED:"DCBrowserExt:LocalFte:GoToSettings:Clicked",LOCAL_FTE_CROSS_BUTTON_CLICKED:"DCBrowserExt:LocalFte:CrossButton:Clicked",LOCAL_FTE_DONT_ASK_CHECKED:"DCBrowserExt:LocalFte:DontAskAgain:Checked",LOCAL_FTE_DONT_ASK_UNCHECKED:"DCBrowserExt:LocalFte:DontAskAgain:Unchecked",LOCAL_FTE_PERMISSION_GRANTED:"DCBrowserExt:LocalFte:LocalFilePermission:Granted",LOCAL_FILE_ACCESS_TOUCHPOINT_PERMISSION_GRANTED:"DCBrowserExt:LocalFileAccessTouchpoint:LocalFilePermission:Granted",LOCAL_FTE_SETTINGS_OPENED:"DCBrowserExt:LocalFte:Settings:Opened:VARIANT",LOCAL_FILE_ACCESS_TOUCHPOINT_SETTINGS_OPENED:"DCBrowserExt:LocalFileAccessTouchpoint:Settings:Opened:VARIANT",LOCAL_FTE_WINDOW_CLOSED:"DCBrowserExt:LocalFte:Window:Closed",LOCAL_FILE_OPTIONS_CLICKED:"DCBrowserExt:Options:LocalFile:STATE:Clicked",LOCAL_FILE_OPENED:"DCBrowserExt:LocalFile:Opened:Permission:Disabled",DOWNLOAD_BANNER_SHOWN:"DCBrowserExt:DownloadBanner:Shown",DOWNLOAD_BANNER_TURN_ON_CLICKED:"DCBrowserExt:DownloadBanner:TurnOn:Clicked",DOWNLOAD_BANNER_MENU_SHOWN:"DCBrowserExt:DownloadBanner:Menu:Shown",DOWNLOAD_BANNER_CLOSE_CLICKED:"DCBrowserExt:DownloadBanner:Close:Clicked",DOWNLOAD_BANNER_DONT_SHOW_AGAIN_CLICKED:"DCBrowserExt:DownloadBanner:DontShowAgain:Clicked",DOWNLOAD_BANNER_PERMISSION_GRANTED:"DCBrowserExt:DownloadBanner:Permission:Granted",DOWNLOAD_BANNER_TOAST_SHOWN:"DCBrowserExt:DownloadBanner:Toast:Shown",DOWNLOAD_BANNER_ENABLED:"DCBrowserExt:DownloadBanner:Enabled",DOWNLOAD_BANNER_MAX_LIMIT_SHOWN:"DCBrowserExt:DownloadBanner:MaxLimit:Shown",EXT_MENU_ICON_CLICKED:"DCBrowserExt:ExtMenu:Icon:Clicked",EXT_MENU_CDN_OFFLINE:"DCBrowserExt:ExtMenu:CDN:Offline",ENABLED_AFTER_READER_REPROMPT:"DCBrowserExt:Enabled:After:Reader:Reprompt",REOPENED_TABS_ON_LOCAL_FILE_ACCESS:"DCBrowserExt:LocalFte:LocalFilePermission:TabsReopened",PDF_CONTENT_TYPE_EVENT:"DCBrowserExt:DocOpen:ContentType:PDF",EXPRESS_CONTEXT_MENU_FG_ENABLED:"DCBrowserExt:Express:ContextMenu:FG:Enabled",EXPRESS_EXECUTE_VERB_FAILED:"DCBrowserExt:Express:ExecuteVerbFailed:VERB",EXPRESS_EXECUTE_VERB_EDITOR_ASSET_LOADED:"DCBrowserExt:Express:ExecuteVerb:AssetLoaded:VERB",EXPRESS_UNSUPPORTED_FILE_TYPE:"DCBrowserExt:Express:UnsupportedFileType:VERB",EXPRESS_TAB_CLOSED_BEFORE_EXPRESS_LOADED:"DCBrowserExt:Express:TabClosedBeforeExpressLoaded",AI_ASSISTANT_MENU_SHOWN:"DCBrowserExt:AIAssistant:Menu:Shown",AI_ASSISTANT_MENU_OPEN_IN_ACROBAT_CLICKED:"DCBrowserExt:AIAssistant:Menu:OpenInAcrobat:Clicked",AI_ASSISTANT_MENU_GET_SUMMARY_CLICKED:"DCBrowserExt:AIAssistant:Menu:GetSummary:Clicked",AI_ASSISTANT_MENU_GET_INSIGHT_CLICKED:"DCBrowserExt:AIAssistant:Menu:GetInsight:Clicked"},this.LOG=()=>null,this.event=async function(E,i){if("false"!==t.getItem("ANALYTICS_OPT_IN_ADMIN")&&C)if(E){i=i||{};try{const{eVars:C,pageName:D}=await async function(E,o,C){e.isEdge()&&(o=o.replace("DCBrowserExt","DCEdgeExt")),o=o.replace(/OPERATION/,E.operation||"Unknown").replace(/ENVIRONMENT/,E.environment).replace(/STAGE/,E.stage).replace(/TIMING/,E.timing).replace(/RANGE/,E.size).replace(/SITE/,E.site).replace(/PROTOCOL/,E.protocol),e.each(C,(function(e,E){o=o.replace(e,E)})),r.ANALYTICS&&e.consoleLog("%c"+o,"color: #ffda94");const i=t.getItem("installType")||"update",D=t.getItem("viewer-enabled-source")||"Unknown",O=t.getItem("viewerVisitorID")||void 0,n="true"===t.getItem("adobeInternal")?"InternalUser":"ExternalUser",T=s(),I=(await _.isMimeHandlerAvailable(),await e.checkOS());let S;if(C?.tabURL){const e=new URL(C.tabURL),E=new URLSearchParams(e.search).get("pdfurl")||C.tabURL;S=new URL(E)?.origin}return C?.domain&&(S=C.domain),{eVars:{eVar1:`${E.version}:${i}`,eVar4:E.shim,eVar22:I,eVar31:D,eVar41:O,eVar50:C?.previousVersion||"Viewer",evar60:E.installType,eVar80:n,evar153:E.environment,eVar233:C?.installReason,...S&&{eVar5:S},...C?.ownershipStatus&&{evar24:C?.ownershipStatus},...C?.gsuiteFte&&{evar32:C?.gsuiteFte},...C?.hasPDFLink&&{evar39:C?.hasPDFLink},...C?.loadTime&&{evar92:C?.loadTime},...C?.dvDisableSessionCount&&{evar37:C?.dvDisableSessionCount},...C?.experimentEnablementStatus&&{evar38:C?.experimentEnablementStatus},...C?.eventContext&&{evar73:C?.eventContext},...T&&{evar6:T}},pageName:o}}(this,E,i),O=chrome.runtime.getURL("");let n;n="development"===this.installType?"f63e90c2-b925-416d-b1ab-680789d02ee6":"716bebe9-4dd6-40c2-a723-7942f40515e4",o.info({message:D,...C,context:"analytics"});return(await fetch(`https://sstats.adobe.com/ee/v1/interact?configId=${n}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({events:[{xdm:{eventType:"web.webpagedetails.pageViews",timestamp:(new Date).toISOString(),web:{webPageDetails:{name:D,URL:O,siteSection:"Acrobat Extension",server:"www.adobe.com",isErrorPage:!1,isHomePage:!1,pageViews:{value:1}},webReferrer:{URL:""}},timestamp:(new Date).toISOString(),_experience:{analytics:{customDimensions:{eVars:C}}}},meta:{state:{cookiesEnabled:!0,domain:"adobe.com"}}}]})})).json()}catch(E){e.consoleError(E)}}else e.consoleError("Missing analytics string")},this.init=async function(){C="false"!==t.getItem("logAnalytics"),this.environment="prod",this.shim="not_set";const e=await chrome.management.getSelf();this.version=e.version,this.installType=await _.isInstalledViaUpsell()?"upsell":e.installType},this.setArg=function(e,E){e&&(this[e]=E)},this.setParamsAndLogAnalytics=function(e,E,r){if(e){var t=this;e.forEach((function(e){t[r]=e,t.event(E)}))}},this.setAnalyticsUsage=function(e,E){C=e,t.setItem("logAnalytics",C.toString())},this.getAnalyticsUsage=function(){return C},this.setOp=function(e){e&&(this.operation=e)},this.cleanErrorAnalyticsString=function(e){if(!e)return"DCBrowser:Error:JS:EVENT_IS_NULL";const E=e.stack?e.stack.match(/([A-Za-z0-9\-]+)\.js:(\d*):(\d*)/):"NO_FILE_IN_STACK",r="string"==typeof e.message?e.message.replace(/\s/g,"_").replace(/"\S*?"/g,"").replace(/'\S*?'/g,""):"NO_MESSAGE_IN_ERROR";return"DCBrowser:Error:JS:"+(E&&E.length>0?E[0]:"")+":"+r},this.error=function(e,E,r){try{this.event(this.e.ERROR_SHOWN);var t=this.cleanErrorAnalyticsString(r);this.event(t)}catch(e){}},E&&E.handlers(this.error.bind(this)),this.checkSizes=function(e){e>0&&e<=1?this.setArg("size","0_1"):e>1&&e<=2?this.setArg("size","1_2"):e>2&&e<=5?this.setArg("size","2_5"):e>5&&e<=10?this.setArg("size","5_10"):e>10&&e<=50?this.setArg("size","10_50"):e>50&&e<=500?this.setArg("size","50_500"):e>500&&e<=1e3?this.setArg("size","500_1000"):e>1e3&&e<=2e3?this.setArg("size","1000_2000"):e>2e3&&e<=3e3?this.setArg("size","2000_3000"):e>3e3&&e<=4e3?this.setArg("size","3000_4000"):e>4e3&&this.setArg("size","4000_")},this.checkAndLogHTMLBlobSize=function(e){this.checkSizes(e),this.event(this.e.HTML_SOURCE_SIZE)},this.checkAndLogPDFSize=function(e){this.checkSizes(e),this.event(this.e.PDF_SOURCE_SIZE)},this.checkAndLogTimingRange=function(e){e>0&&e<=5?this.setArg("timing","0_5"):e>5&&e<=10?this.setArg("timing","5_10"):e>10&&e<=20?this.setArg("timing","10_20"):e>20&&e<=30?this.setArg("timing","20_30"):e>30&&e<=50?this.setArg("timing","30_50"):e>50&&e<=100?this.setArg("timing","50_100"):e>100&&e<=200?this.setArg("timing","100_200"):e>200&&e<=600?this.setArg("timing","200_600"):e>600&&e<=1200?this.setArg("timing","600_1200"):e>1200&&e<=3e3?this.setArg("timing","1200_3000"):e>3e3&&this.setArg("timing","3000_"),this.event(this.e.HTML_CONVERSION_STAGE_TIMING)},this.logSiteAndProtocolAnalytics=function(e){var E,r,t,_,o=[],s=[];0!==e.indexOf("chrome:")&&(t=this.parseURL(e),r=/^(http|https):\/\/www/.test(e),E=/^(([0-9]+\.){3}([0-9]+))$/.test(e),_=t.hostname.split(".").reverse()[0].toLowerCase(),r&&o.push("WWWW"),E&&o.push("IP"),"com"!==_&&"org"!==_&&"net"!==_&&"int"!==_&&"edu"!==_&&"gov"!==_&&"mil"!==_||o.push("TLD"),s.push(t.protocol),this.setParamsAndLogAnalytics(s,this.e.HTML_SOURCE_PROTOCOL,"protocol"),this.setParamsAndLogAnalytics(o,this.e.HTML_SOURCE_SITE,"site"))},this.parseURL=function(e){const E=new URL(e);return{protocol:E.protocol.slice(0,E.protocol.length-1),host:E.host,hostname:E.hostname,port:E.port,pathname:E.pathname}},this.logBrowserAnalytics=function(e){e.analytics&&(e.analytics.forEach(this.proxy((function(e){e instanceof Array?this.checkAndLogAnalytics(...e):this.checkAndLogAnalytics(e)}))),delete e.analytics)},this.logContents=function(e){e.content_analytics&&(e.content_analytics.forEach(this.proxy((function(e){this.event(this.e.HTML_SOURCE_CONTENT,{CONTENT:e})}))),delete e.analytics)},this.checkAndLogAnalytics=function(E,r={}){r=r||{};var _,o="TIREKICK";E?(-1!==E.indexOf(o)&&((_=t.getItem(o))?-1!==_.indexOf(E)?r[o]="Subsequent":(t.setItem(o,_+"|"+E),r[o]="FirstTime"):(t.setItem(o,E),r[o]="FirstTime")),this.event(E,r)):e.consoleError("Missing analytics string")},this.logError=function(e){var E=e;"web2pdfHTMLTooLarge"===e&&(E=this.e.HTML_SOURCE_SIZE_TOO_LARGE_ERROR),this.event(E)},this.logEventOnce=function(e,E={}){const{storageKey:r,..._}=E;if(r){t.getItem(r)||(this.event(e,_),t.setItem(r,!0))}}};i.init();const D=i.e;export{i as analytics,D as events};