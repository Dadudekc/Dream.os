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
var dialogToBeReopened;function createDomAnchor(e,t=2147483646){if(document.querySelector(`#${e}`))return document.querySelector(`#${e}`);const o=document.createElement("div");return o.id=e,o.style.position="fixed",o.style.zIndex=`${t}`,o.style.width="100%",o.style.height="100%",o.style.top="0",o.style.colorScheme="light",o.style.backgroundColor="rgba(0, 0, 0, 0.5)",o.style.display="block",document.body.style.overflow="hidden",o}function openExpressEditorInFrame(){const e=new URL(window.location.href).hostname,t=createDomAnchor("expressAcrobatExtension"),o=chrome.runtime.getURL("browser/js/express.html")+`?domain=${e}`,r=document.createElement("iframe");r.setAttribute("src",o),r.setAttribute("id","expressAcrobatExtensionIframe"),r.setAttribute("allowfullscreen","true"),r.setAttribute("allow","clipboard-read; clipboard-write;"),r.style.width="100%",r.style.height="100%",r.style.border="none",r.style.overflow="hidden";const n=document.getElementsByTagName("dialog");for(let e of n)if(e&&e.open){dialogToBeReopened=e,e.close();break}t.appendChild(r),document.body.insertBefore(t,document.body.childNodes[0])}openExpressEditorInFrame();