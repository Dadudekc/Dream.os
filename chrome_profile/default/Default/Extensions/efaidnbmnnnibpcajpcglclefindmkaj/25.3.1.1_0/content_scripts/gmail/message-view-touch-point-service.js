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
import{createAcrobatIconElement,createURLForAttachment,getArrayElementBasedOnSelector,getClosestElementBasedOnSelector,getElementBasedOnSelector,updateDrivePDFUrl,isDriveFileDirectDownloadLink,isDriveLinkAttachmentTouchPointEnabled}from"./util.js";import{isDefaultViewer,sendAnalyticsWithGMailDVFeatureStatus,openPdfInNewTab}from"./default-viewership-service.js";import{sendAnalytics}from"../gsuite/util.js";import{acrobatTouchPointClicked,createFteTooltip,getAcrobatTouchPointFteEligibility,removeGsuiteFteTooltip,shouldShowFteTooltip,updateFteToolTipCoolDown}from"../gsuite/fte-utils.js";import state from"./state.js";import{processForNativeViewer}from"./native-viewer-touch-point-service.js";const ATTACHMENT_CARD_HYPERLINK_CLASS="acrobat-attachmentcard-hyperlink",ACROBAT_PROCESSED_ATTRIBUTE="acrobat-icon-added",GMAIL_FTE_TOOLTIP_STORAGE_KEY="acrobat-gmail-fte-config",GMAIL_FTE_TOOLTIP_CONTAINER_CLASS="acrobat-fte-tooltip-container",getMessageView=()=>getArrayElementBasedOnSelector(document,"messageView","messageView"),getParentElementForAcrobatIcon=e=>getElementBasedOnSelector(e,"attachmentCardParentElementForAcrobatIcon","messageView"),getAttachmentCardElement=e=>getClosestElementBasedOnSelector(e,"attachmentCardElement","messageView"),createAcrobatTooltip=()=>{const e=document.createElement("div");return e.setAttribute("class","acrobat-attachmentcard-tooltip"),e.innerText=state?.gmailConfig?.acrobatPromptText,e},handleAcrobatHyperLinkClickForFteToolTip=e=>{const t=document.getElementsByClassName("acrobat-fte-tooltip-container");t?.length>0&&(e.style.removeProperty("z-index"),sendAnalytics(["DCBrowserExt:GmailFTE:MessageView:Dismissed"])),acrobatTouchPointClicked("acrobat-gmail-fte-config"),state.fteToolTip.eligibleFte.type="",state.fteToolTip.touchPointClicked=!0},createAcrobatHyperlinkForAttachmentCard=(e,t,o)=>{e=createURLForAttachment(e,"GmailAttachmentCard",t);const a=document.createElement("a");a.setAttribute("class",ATTACHMENT_CARD_HYPERLINK_CLASS),a.setAttribute("href",e),a.setAttribute("target","_blank"),a.addEventListener("click",(()=>{let t="DCBrowserExt:Gmail:AttachmentCardPrompt:Clicked";isDriveFileDirectDownloadLink(e)&&(t="DCBrowserExt:Gmail:AttachmentCardPrompt_DriveLink:Clicked"),sendAnalytics([[t,{gsuiteFte:getAcrobatTouchPointFteEligibility(state?.gmailConfig?.enableGmailFteToolTip)}]]),handleAcrobatHyperLinkClickForFteToolTip(o)}),{signal:state?.eventControllerSignal});const n=createAcrobatIconElement(),i=createAcrobatTooltip();return a.appendChild(n),a.appendChild(i),a},getMessageViewPDFAttachmentsWithoutAcrobatIcon=()=>{const e=getMessageView();let t=[];if(e&&e.length>0)for(let o=0;o<e.length;o++){const a=e[o],n=getArrayElementBasedOnSelector(a,"pdfAttachmentWithoutAcrobatIcon","messageView");n&&n.length>0&&t.push(...n)}return t},addFteTooltipButtonEventListener=(e,t)=>{e.querySelector(".acrobat-fte-tooltip-button").addEventListener("click",(()=>{removeGsuiteFteTooltip(),state.fteToolTip.eligibleFte.type="",t?.style?.removeProperty("z-index"),sendAnalytics(["DCBrowserExt:GmailFTE:MessageView:Clicked"])}))},addFteTooltipToAttachmentCard=e=>{const t=createFteTooltip(state?.gmailConfig?.gmailFteToolTipStrings,"messageView");addFteTooltipButtonEventListener(t),e.appendChild(t),sendAnalyticsWithGMailDVFeatureStatus(["DCBrowserExt:GmailFTE:MessageView:Shown"]),updateFteToolTipCoolDown(state?.gmailConfig?.fteConfig?.tooltip,"acrobat-gmail-fte-config").then((e=>{state.fteToolTip={...state?.fteToolTip,...e}}))},handleMouseEnterEventForCardElementWithFTETooltip=e=>{const t=e.getElementsByClassName("acrobat-fte-tooltip-container");t?.length>0&&(e.style.zIndex="2",t[0].style.removeProperty("display"))};function addFTETooltipToAttachmentCardIfEligible(e,t){const o=state?.gmailConfig?.fteConfig?.tooltip;shouldShowFteTooltip(o,state?.fteToolTip,state?.gmailConfig?.enableGmailFteToolTip).then((o=>{o&&(e.style.zIndex="2",addFteTooltipToAttachmentCard(t))}))}const attachmentCardMouseOverEventListener=(e,t)=>{e.addEventListener("mouseenter",(()=>{handleMouseEnterEventForCardElementWithFTETooltip(e),addFTETooltipToAttachmentCardIfEligible(e,t)}),{signal:state?.eventControllerSignal})},attachmentCardMouseOutEventListener=e=>{e.addEventListener("mouseleave",(()=>{const t=e.getElementsByClassName("acrobat-fte-tooltip-container");t?.length>0&&(t[0].style.display="none",e.style.removeProperty("z-index"))}),{signal:state?.eventControllerSignal})},handleFteTooltipForAttachmentCard=(e,t)=>{attachmentCardMouseOverEventListener(e,t),attachmentCardMouseOutEventListener(e)},handleClickAction=(e,t,o)=>{if("click"===e.type||"keydown"===e.type&&"Enter"===e.key){if(isDefaultViewer())e.preventDefault(),e.stopPropagation(),openPdfInNewTab({url:o?.url,touchPoint:"GmailAttachmentCard",attachmentName:o?.name});else{const e=document.getElementsByClassName("acrobat-fte-tooltip-container");e?.length>0&&(t.style.removeProperty("z-index"),removeGsuiteFteTooltip(),state.fteToolTip.eligibleFte.type="",sendAnalytics(["DCBrowserExt:GmailFTE:MessageView:Dismissed"])),setTimeout((()=>processForNativeViewer({url:o?.url})),500),setTimeout((()=>processForNativeViewer({url:o?.url})),1e3)}sendAnalyticsWithGMailDVFeatureStatus([`DCBrowserExt:Gmail:AttachmentCard${o?.isDriveAsset?"_DriveLink":""}:Clicked`])}},addAttachmentCardHyperlinkEventListener=(e,t,o)=>{e?.addEventListener("click",(e=>handleClickAction(e,t,o)),{signal:state?.eventControllerSignal}),e?.addEventListener("keydown",(e=>handleClickAction(e,t,o)),{signal:state?.eventControllerSignal})},addAcrobatIconToAttachmentCard=e=>{e?.forEach((e=>{const t=e?.closest("a");let o=t?.getAttribute("href"),a=!1;if(o&&o.includes("drive.google.com")||o.includes("docs.google.com")){if(!isDriveLinkAttachmentTouchPointEnabled())return void e.setAttribute("acrobat-icon-added","Y");a=!0,o=updateDrivePDFUrl(o)}const n=getAttachmentCardElement(e),i=getParentElementForAcrobatIcon(n);if(o&&i){const r=getElementBasedOnSelector(t,"attachmentName","messageView")?.textContent;if(!isDefaultViewer()){const e=createAcrobatHyperlinkForAttachmentCard(o,r,n);handleFteTooltipForAttachmentCard(n,e),i.appendChild(e)}e.setAttribute("acrobat-icon-added","Y");addAttachmentCardHyperlinkEventListener(t,n,{url:o,name:r,isDriveAsset:a})}}))},addAcrobatTouchPointInTheMessageView=()=>{try{const e=getMessageViewPDFAttachmentsWithoutAcrobatIcon();e&&e.length>0&&addAcrobatIconToAttachmentCard(e)}catch(e){sendAnalytics([["DCBrowserExt:Gmail:MessageView:ProcessingFailed"]])}},removeAllTouchPoints=()=>{const e=document.querySelectorAll(`.${ATTACHMENT_CARD_HYPERLINK_CLASS}`);if(e?.length>0){const t=document.getElementsByClassName("acrobat-fte-tooltip-container");t?.length>0&&sendAnalytics(["DCBrowserExt:GmailFTE:MessageView:Dismissed"]);for(let t=0;t<e.length;t++)e[t]?.parentElement?.removeChild(e[t])}};export{addAcrobatTouchPointInTheMessageView,removeAllTouchPoints};