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
const NonePrompt={id:"None"};class ShowOneChild{constructor({dcLocalStorage:e,dcSessionStorage:t}){this.dcLocalStorage=e,this.dcSessionStorage=t,this.prompts=[],this.render(),this.subscribeToPromptEvents()}sendMessage=(e,t)=>{chrome.runtime.sendMessage({main_op:"relay_to_content",shouldCache:!1,...e},t)};subscribeToPromptEvents=()=>{chrome.runtime.onMessage.addListener((e=>{switch(e.action){case"clearRenderPrompt":this.dcLocalStorage.removeItem("renderPrompt");break;case"reRenderShowOneChild":this.render()}}))};setRenderPromptTTL=e=>{this.dcLocalStorage.setWithTTL("renderPrompt",e?.id,864e5)};lockRenderPrompt=()=>{this.dcLocalStorage.setWithTTL("renderPrompt","locked",5e3)};releaseLock=()=>{this.dcLocalStorage.removeItem("renderPrompt")};readRenderPromptFromStorage=async()=>{let e=0,t=this.dcLocalStorage.getWithTTL("renderPrompt");for(;"locked"===t;){if(e>=10)return NonePrompt;await new Promise((t=>setTimeout(t,200*(e+1)))),e++,t=this.dcLocalStorage.getWithTTL("renderPrompt")}return t};generateEligibilityPromise=e=>new Promise((t=>{let r=!1;const o=setTimeout((()=>{r||t(!1)}),2e3);this.sendMessage({action:"isEligible",promptId:e},(e=>{clearTimeout(o),r=!0,t(e)}))}));getRenderPrompt=async()=>{const e=await this.readRenderPromptFromStorage();if(this.prompts.some((t=>t.id===e)))return this.dcLocalStorage.updateWithTTL("renderPrompt","None"),NonePrompt;this.lockRenderPrompt();for(const e of this.prompts)e.eligiblityPromise=this.generateEligibilityPromise(e.id);for(prompt of this.prompts){if(await prompt.eligiblityPromise)return this.setRenderPromptTTL(prompt),prompt}return this.releaseLock(),NonePrompt};render=async()=>{const e=await this.getRenderPrompt();this.sendMessage({action:"renderPrompt",promptId:e?.id})}}const dcLocalStorageUrl=chrome.runtime.getURL("common/local-storage.js");import(dcLocalStorageUrl).then((async({dcLocalStorage:e,dcSessionStorage:t})=>{await e.init(),await t.init(),new ShowOneChild({dcLocalStorage:e,dcSessionStorage:t})}));