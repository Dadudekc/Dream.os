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
import{dcLocalStorage as e}from"../../common/local-storage.js";import{events as t}from"../../common/analytics.js";import{LOCAL_FILE_PERMISSION_URL as n,LOCAL_FTE_WINDOW as i,validFrictionlessLocales as o,PIN_TOOLBAR_URL as r}from"../../common/constant.js";import{dcTabStorage as s}from"./tab-storage.js";import{SETTINGS as a}from"../../sw_modules/settings.js";await e.init();export const util={getFrictionlessLocale:e=>o[e]||o.en,analytics:function(e,t,n){e.analytics||(e.analytics=[]),e.analytics.push([t,n])},messageToMain:function(e,t){chrome.runtime.sendMessage(e,t)},addMainListener:function(e){chrome.runtime.onMessage.addListener(e)},isChrome:function(){return!0},isEdge:function(){try{if("true"===e.getItem("IsRunningInEdge"))return!0}catch(e){}let t=window.navigator.userAgent.toLowerCase();return-1!==t.indexOf("chrome")&&-1!==t.indexOf("edg/")},isChromeOnlyMessage:function(e){return-1!==["web2pdfMissingMac","web2pdfFrictionlessUrl","web2pdfBadVersion","pdfOwnershipExploreAcrobat","pdfOwnershipPromptContent","LearnMoreURL"].indexOf(e)},consoleLog:function(...e){a.DEBUG_MODE&&console.log(...e)},consoleLogDir:function(...e){a.DEBUG_MODE&&console.dir(...e)},consoleError:function(...e){a.DEBUG_MODE&&console.error(...e)},getTranslation:function(e,t){if(e)return util&&util.isChromeOnlyMessage(e)&&util.isEdge()&&(e+="Edge"),t?chrome.i18n.getMessage(e,t):chrome.i18n.getMessage(e)},translateElements:function(e){$(e).each((function(){"INPUT"===this.tagName?$(this).val(util.getTranslation(this.id)):$(this).text(util.getTranslation(this.id))}))},getSearchParamFromURL:function(e,t){const n=new URL(t);return new URLSearchParams(n.search).get(e)},isPDFForm:function(e){let t=/.+?\:\/\/.+?(\/.+?)(?:#|\?|$)/.exec(e),n="";if(null===t||t.length<2)return!1;if(n=t[1].endsWith("/")?t[1].slice(0,-1):t[1],void 0===n||0==n.length)return!1;n=n.toLowerCase();let i=n.split("/"),o=i[i.length-1];function r(e){return o.indexOf(e)>-1}return!["forms","guide","summary","process","sample","procedure","requirement","example","instr","format","formul","reform","forming","former","formed"].some(r)&&(!!(i.length>1&&(i.pop(),i.includes("form")||i.includes("forms")))||["form","application.pdf"].some(r))},logSharePointAnalytics:function(e,n){a.FILL_N_SIGN_ENABLED&&"FillnSign"===e.paramName?n?e.version===a.READER_VER?util.analytics(e,t.TREFOIL_FILLSIGN_READER_SHAREPOINT):util.analytics(e,t.TREFOIL_FILLSIGN_ACROBAT_SHAREPOINT):e.version===a.READER_VER?util.analytics(e,t.PERSIST_FILLSIGN_READER_SHAREPOINT):util.analytics(e,t.PERSIST_FILLSIGN_ACROBAT_SHAREPOINT):n?e.version===a.READER_VER?util.analytics(e,t.TREFOIL_PDF_READER_SHAREPOINT):util.analytics(e,t.TREFOIL_PDF_ACROBAT_SHAREPOINT):e.version===a.READER_VER?util.analytics(e,t.PERSIST_PDF_READER_SHAREPOINT):util.analytics(e,t.PERSIST_PDF_ACROBAT_SHAREPOINT)},logOpenInAcrobatAnalytics:function(e,n){let i=t.PERSIST_PDF_ACROBAT;i=a.FILL_N_SIGN_ENABLED&&"FillnSign"===e.paramName?n?e.version===a.READER_VER?t.TREFOIL_PDF_READER_FS:t.TREFOIL_PDF_ACROBAT_FS:e.version===a.READER_VER?t.PERSIST_PDF_READER_FS:t.PERSIST_PDF_ACROBAT_FS:n?e.version===a.READER_VER?t.TREFOIL_PDF_READER:t.TREFOIL_PDF_ACROBAT:e.version===a.READER_VER?t.PERSIST_PDF_READER:t.PERSIST_PDF_ACROBAT,util.analytics(e,i)},handleXHRRequest:function(e,t,n,i){let o=new XMLHttpRequest;o.onreadystatechange=function(){o.readyState===XMLHttpRequest.DONE&&(200===o.status?i(null,o):i(o.status,null))},o.ontimeout=function(e){i(e,null)},o.onerror=function(e){i(e,null)},o.open(e,t,!0),o.send(n)},handlePDFURL:async function(e,t=!0){if(!0===a.SHAREPOINT_ENABLED){if(e.isSharePointURL)return util.logSharePointAnalytics(e,t),e;{const n=await util.checkForSharePointURL(e.url);return e.isSharePointURL=n,n?util.logSharePointAnalytics(e,t):util.logOpenInAcrobatAnalytics(e,t),e}}return e.isSharePointURL=!1,util.logOpenInAcrobatAnalytics(e,t),e},checkForSharePointURL:function(e){return new Promise((t=>{util.handleXHRRequest("OPTIONS",e,null,((n,i)=>{if(!n&&i){let n=i.getResponseHeader("MicrosoftSharepointTeamServices"),o=i.getResponseHeader("MS-Author-Via");if(n&&o&&o.includes("MS-FP/4.0")){const n=new URL(e),i=n.protocol+"//"+n.hostname+":"+n.port+"/_vti_inf.html";return void util.handleXHRRequest("GET",i,null,((e,n)=>{if(!e&&n){let e=n.response;if(e.includes("FPAuthorScriptUrl")&&e.includes("FPAdminScriptUrl"))return void t(!0)}t(!1)}))}}t(!1)}))}))},uuid:function(){try{let e=(new Date).getTime();return"xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g,(function(t){let n=(e+16*Math.random())%16|0;return e=Math.floor(e/16),("x"===t?n:3&n|8).toString(16)}))}catch(e){return Math.random()}},sendAnalytics:e=>chrome.runtime.sendMessage({main_op:"analytics",analytics:[e]}),getAppCode:()=>util.isEdge()?"adobe.com_acrobatextension_edge_login":"adobe.com_acrobatextension_chrome_login",generateStateCSRF:()=>{const e=util.uuid(),t={csrf:e};return s.setItem("csrf",e),t},openExtensionSettingsInWindow:({tab:t,action:o},s)=>{let a="";a="pinToolbar"===o?r:n,chrome.windows.get(t.windowId,(function(t){const{height:n}=i,o=Math.round(1.2*i.width),r=Math.round(.5*(t.height-n)+t.top),l=Math.round(.5*(t.width-o)+t.left);chrome.windows.create({height:n,width:o,left:l,top:r,focused:!0,type:"popup",url:a},(t=>{e.setItem("settingsWindow",t),s&&s(t)}))}))}};