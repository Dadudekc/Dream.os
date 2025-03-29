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
import{analytics as e,events as t}from"../../common/analytics.js";import{dcLocalStorage as o}from"../../common/local-storage.js";import{loggingApi as n}from"../../common/loggingApi.js";import{common as a}from"../../sw_modules/common.js";import{EXPRESS as r}from"../../sw_modules/constant.js";import{Deferred as s}from"../../sw_modules/polyfills.js";import{PromiseTimeout as i}from"../../sw_modules/TimeoutPromise.js";import{util as l}from"../../sw_modules/util.js";import{verbNameToIntent as c,imageUrlToBase64 as d}from"../../sw_modules/express.js";(async()=>{const m="expressPluginIframe";let p,g,E,u,_,f,T,h,w,b,S,D,x,y,I,L,O=["image/jpeg","image/png","image/webp"];function A(){const e=document.getElementById("loaderId");e&&e.parentNode&&e.parentNode.removeChild(e)}function R(){chrome.runtime.sendMessage({main_op:"removeTabIdFromUnloadedExpressTabs"})}function C(e){let t=chrome.runtime.getURL("browser/js/failToast.html");e&&(t+="?errorType="+e);var o=$("#expressAcrobatExtensionIframe");0===o.length?(o=$("<iframe>")).attr("id","expressAcrobatExtensionIframe").css({border:"0px","z-index":2147483647,position:"fixed",width:"525px",height:"50px",display:"block",margin:"auto",background:"transparent","color-scheme":"auto",bottom:"50px",right:"calc(50% - 250px)","border-radius":"4px"}).attr("src",t).appendTo("html"):"none"===o.css("display")&&o.css({display:"block"})}function U(o){R(),e.event(t.EXPRESS_EXECUTE_VERB_FAILED,{VERB:_,eventContext:o}),n.error({message:"Error received in express flow",error:o})}function M(e){const t=[{id:"extension_download",label:l.getTranslation("expressExportOptionsDownloadLabel"),action:{target:"publish",closeTargetOnExport:!1},style:{uiType:"button"}}];return{type:"LAUNCH_MODULE",data:{hostInfo:{clientId:a.getViewerIMSClientId(),appName:"Adobe Acrobat Extension"},intent:"edit-image",component:"MODULE",configParams:{locale:o.getItem("appLocale")||l.getFrictionlessLocale(chrome.i18n.getMessage("@@ui_locale")),env:a.getEnv()},appConfig:{allowedFileTypes:["image/png"],metaData:{touStatus:o.getItem(r.TOU_ACCEPTED)},publishModalTitle:l.getTranslation("expressPublishModalTitle")},docConfig:e,exportConfig:t}}}function P(){u.then((o=>{let a=o.base64data;T=o.imageDownloadTime,h=a.length;const s={"data:image/jpeg;":["data:binary/octet-stream;","data:application/octet-stream;","data:image/jpg;"],"data:image/png;":["data:img/png;"]};for(let e of Object.keys(s))for(let t of s[e])a=a.replace(t,e);const i=a.substring(a.indexOf(":")+1,a.indexOf(";"));if(function(e){return O.includes(e)}(i)){const e={asset:{data:a,dataType:"base64",type:"image"}};_!==r.VERBS.EDIT_IMAGE&&(e.intent=c(_));let t=M(e);const o=document.getElementById(m);w=Date.now()-f,o.contentWindow.postMessage(t,g.origin)}else{R(),A(),C("unsupportedFileType");const o=new URLSearchParams(window.location.search).get("domain");e.event(t.EXPRESS_UNSUPPORTED_FILE_TYPE,{VERB:_,eventContext:i,domain:o}),n.error({message:"Error received in express flow",error:"Unsupported image type",fileType:i})}})).catch((e=>{A(),C(),U(e.toString())}))}try{await o.init(),function(){f=Date.now();const e=o.getItem("env");a.reset(e),p=a.getExpressURLs().pluginUrl,g=new URL(p),E=o.getItem(r.CONTEXT_MENU_ON_CLICK_INFO_LOCAL_STORAGE_KEY),o.removeItem(r.CONTEXT_MENU_ON_CLICK_INFO_LOCAL_STORAGE_KEY),u=d(E.srcUrl),_=E.menuItemId.replace("ContextMenu","")}(),window.addEventListener("message",(a=>{try{if(a.origin===g.origin)switch(a.data?.type){case"EMBED_SDK_ON_LOAD":A(),document.querySelector(`#${m}`).focus();break;case"EMBED_SDK_EVENT":switch(a.data.data?.type){case"ASSET_LOADED":R();const s=Date.now()-f,i={loadTime:s,imageDownloadTime:T,timeRequiredToHandoverToExpress:w,expressPluginLoadingTime:S,imageSize:h,VERB:_},l=r.PERF_METRIC_LOG_MESSAGE;"true"===o.getItem("adobeInternal")&&(console.log("Express Plugin Loading Time "+S),console.log("Express Supported Image Types Fetching Time "+x),console.log("Image Download Time "+T),console.log("Time required to handover to express "+w),console.log(l+" "+s)),n.info({message:l,...i}),e.event(t.EXPRESS_EXECUTE_VERB_EDITOR_ASSET_LOADED,i);break;case"SET_TOU_STATE":o.setItem(r.TOU_ACCEPTED,JSON.stringify(a.data?.data?.data?.data))}break;case"EMBED_SDK_READY":I.resolve(),S=Date.now()-b,D=Date.now(),document.getElementById(m).contentWindow.postMessage({type:"REQUEST_MODULE_SUPPORTED_IMAGE_TYPES"},g.origin),L=s(),y=i(L.promise(),1e3),y.catch((e=>{U("unsupported file types fetching flow "+e.toString()),P()}));break;case"MODULE_SUPPORTED_IMAGE_TYPES":L.resolve(),x=Date.now()-D,O=a.data.data??O,P();break;case"EMBED_SDK_PUBLISH":const l=a.data.data?.asset[0];if(l)try{const e="image."+l.fileType?.split("/")[1];!function(e,t,o){let n=e.split(",")[1],a=atob(n),r=new ArrayBuffer(a.length),s=new Uint8Array(r);for(let e=0;e<a.length;e++)s[e]=a.charCodeAt(e);let i=new Blob([r],{type:o}),l=URL.createObjectURL(i);chrome.downloads.download({url:l,filename:t,conflictAction:"uniquify"},(function(e){chrome.downloads.onChanged.addListener((function t(o){o.id===e&&o.state&&"complete"===o.state.current&&(l&&URL.revokeObjectURL(l),chrome.downloads.onChanged.removeListener(t))})),chrome.runtime.lastError&&U(chrome.runtime.lastError)}))}(l.data,e,l.fileType)}catch(e){U(e.toString())}else U("No asset data found while publishing");break;case"EMBED_SDK_CANCEL":chrome.runtime.sendMessage({main_op:"closeExpressApp"});break;case"EMBED_SDK_ERROR":A(),C(),U("EMBED_SDK_ERROR "+a.data.data?.message)}}catch(e){A(),C(),U("Express Message Listener "+e.toString())}})),function(){b=Date.now();const e=document.createElement("iframe");e.setAttribute("src",p),e.setAttribute("id",m),e.setAttribute("allowfullscreen","true"),e.setAttribute("style","position:fixed; top:0; left:0; bottom:0; right:0; width:100%; height:100%; border:none; margin:0; padding:0; overflow:hidden; z-index:999999;"),document.body.appendChild(e),I=s(),y=i(I.promise(),1e4),y.catch((e=>{A(),C(),U("embed sdk ready flow "+e.toString())}))}()}catch(e){A(),C(),U("Init Express Content Script "+e.toString())}})();