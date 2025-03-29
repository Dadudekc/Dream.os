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
let initialQuestion;class ActionableCoachmark{constructor(){if(ActionableCoachmark.instance)return ActionableCoachmark.instance;ActionableCoachmark.instance=this,this.shadowRoot=null}sendAnalyticsEvent=e=>{try{chrome.runtime.sendMessage({main_op:"analytics",analytics:e})}catch(e){}};async clickHandler(e){this.remove(),await initDcLocalStorage();const t=window.dcLocalStorage.getItem("showActionableCoachmarkConfig")||{};window.dcLocalStorage.setItem("showActionableCoachmarkConfig",{...t,hasUsedActionableCoachMark:!0}),chrome.runtime.sendMessage({type:"open_side_panel",touchpoint:"actionableCoachmark",initialQuestion:e}),this.sendAnalyticsEvent([["DCBrowserExt:SidePanel:ActionableCoachmark:Clicked"]]),initialQuestion=e}isRendered(){return Boolean(this.shadowRoot)}remove(){this.shadowRoot?.host?.remove(),this.shadowRoot=null,this.sendAnalyticsEvent([["DCBrowserExt:SidePanel:ActionableCoachmark:Removed"]]);(new FABManager).renderFAB()}render(){if(this.isRendered())return;const e=document.createElement("div");e.id="aiAcShadowRoot",e.style.display="block",this.shadowRoot=e.attachShadow({mode:"open"}),fetch(chrome.runtime.getURL("resources/SidePanel/ActionableCoachmark.html")).then((e=>e.text())).then((t=>{const o=document.createElement("template");o.innerHTML=t;const n=o.content;this.shadowRoot.appendChild(n.cloneNode(!0)),this.shadowRoot.querySelector(".close-btn").addEventListener("click",(()=>{this.remove()}));const a=this.shadowRoot.querySelector(".nudgeInput");AnimateCannedQuestions.start(a),a.addEventListener("keydown",(e=>{"Enter"===e.key&&this.clickHandler(AnimateCannedQuestions.getQuestion())}));this.shadowRoot.querySelector(".submitBtn").addEventListener("click",(async()=>{this.clickHandler(AnimateCannedQuestions.getQuestion())})),util.translateElements(".translate",this.shadowRoot),document.body.appendChild(e),this.sendAnalyticsEvent([["DCBrowserExt:SidePanel:ActionableCoachmark:Displayed"]])}))}async shouldShow(){if(!await GenAIWebpageEligibilityService.shouldShowTouchpoints())return!1;if(await GenAIWebpageEligibilityService.shouldDisableTouchpoints())return!1;await initDcLocalStorage();const e=window.dcLocalStorage.getItem("showActionableCoachmarkConfig")||{};if(e.hasUsedActionableCoachMark)return!1;const t=e.lastShownTimestamp,o=e.showCount||0,n=()=>(new Date).getTime();return(!t||parseInt(o)<3&&(a=t,i=10,n()-a>=24*i*60*60*1e3))&&(window.dcLocalStorage.setItem("showActionableCoachmarkConfig",{lastShownTimestamp:n(),showCount:parseInt(o)+1}),!0);var a,i}}