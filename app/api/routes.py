"""API routes for the image realism enhancement service."""

import base64
import uuid
from pathlib import Path
from typing import Dict

import aiofiles
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from PIL import Image
import io

from app.config import get_settings
from app.models.schemas import (
    UploadResponse,
    JobResponse,
    JobStatus,
    PipelineResult,
)
from app.pipeline.orchestrator import get_orchestrator

router = APIRouter()

# In-memory job storage (use Redis/DB in production)
jobs: Dict[str, dict] = {}

settings = get_settings()


@router.get("/", response_class=HTMLResponse)
async def web_ui():
    """Web UI for uploading an image and viewing analysis + enhancement results."""
    return HTMLResponse(
        content="""
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>图像真实感增强引擎 - 专家系统</title>
    <style>
      * { box-sizing: border-box; }
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; color: #333; }
      .container { max-width: 1200px; margin: 0 auto; }
      h1 { font-size: 24px; margin: 0 0 8px; color: #111; }
      .subtitle { color: #666; margin-bottom: 20px; }
      
      .card { background: white; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
      .card-title { font-size: 16px; font-weight: 600; margin: 0 0 12px; display: flex; align-items: center; gap: 8px; }
      .card-title .icon { width: 24px; height: 24px; background: #e0e7ff; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
      
      .upload-area { border: 2px dashed #d1d5db; border-radius: 12px; padding: 40px; text-align: center; cursor: pointer; transition: all 0.2s; }
      .upload-area:hover { border-color: #6366f1; background: #f5f3ff; }
      .upload-area.dragover { border-color: #6366f1; background: #f5f3ff; }
      .upload-area input { display: none; }
      
      .controls { display: flex; gap: 12px; margin-top: 16px; flex-wrap: wrap; }
      button { background: #4f46e5; color: white; border: 0; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; }
      button:hover { background: #4338ca; }
      button:disabled { background: #9ca3af; cursor: not-allowed; }
      button.secondary { background: #e5e7eb; color: #374151; }
      button.secondary:hover { background: #d1d5db; }
      
      .images-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
      @media (max-width: 768px) { .images-row { grid-template-columns: 1fr; } }
      .image-box { text-align: center; }
      .image-box img { max-width: 100%; max-height: 400px; border-radius: 8px; border: 1px solid #e5e7eb; }
      .image-label { font-size: 14px; color: #666; margin-bottom: 8px; }
      
      .tag { display: inline-block; padding: 4px 10px; border-radius: 999px; font-size: 12px; margin: 2px; }
      .tag-scene { background: #dbeafe; color: #1e40af; }
      .tag-attr { background: #f3e8ff; color: #6b21a8; }
      .tag-high { background: #fee2e2; color: #991b1b; }
      .tag-medium { background: #fef3c7; color: #92400e; }
      .tag-low { background: #d1fae5; color: #065f46; }
      .tag-agent { background: #e0e7ff; color: #3730a3; font-weight: 500; }
      
      .signal-item { padding: 8px 12px; background: #f9fafb; border-radius: 6px; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
      .signal-severity { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
      .signal-severity.high { background: #ef4444; }
      .signal-severity.medium { background: #f59e0b; }
      .signal-severity.low { background: #10b981; }
      
      .iteration-card { background: #f9fafb; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #4f46e5; }
      .iteration-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
      .iteration-number { font-weight: 600; color: #4f46e5; }
      .iteration-likelihood { font-size: 13px; }
      .likelihood-change { font-weight: 600; }
      .likelihood-change.improved { color: #059669; }
      .likelihood-change.same { color: #6b7280; }
      
      .agent-result { background: white; border-radius: 6px; padding: 12px; margin-top: 8px; }
      .agent-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
      .agent-icon { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
      .agent-icon.skin { background: #fce7f3; }
      .agent-icon.lighting { background: #fef3c7; }
      .agent-icon.texture { background: #d1fae5; }
      .agent-icon.geometry { background: #e0e7ff; }
      .agent-icon.color { background: #fae8ff; }
      .agent-icon.expression { background: #fef3c7; }
      .agent-name { font-weight: 500; }
      .agent-changes { font-size: 13px; color: #666; margin-top: 4px; }
      .agent-changes li { margin-bottom: 2px; }
      
      .prompt-box { background: #1e1e1e; border-radius: 8px; padding: 12px; margin-top: 8px; font-family: monospace; font-size: 12px; }
      .prompt-section { margin-bottom: 12px; }
      .prompt-label { color: #9ca3af; font-size: 11px; text-transform: uppercase; margin-bottom: 4px; }
      .prompt-positive { color: #86efac; }
      .prompt-negative { color: #fca5a5; }
      .prompt-preservation { color: #93c5fd; }
      .prompt-correction { color: #fbbf24; }
      .prompt-intensity { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 8px; }
      .prompt-intensity.light { background: #d1fae5; color: #065f46; }
      .prompt-intensity.medium { background: #fef3c7; color: #92400e; }
      .prompt-intensity.strong { background: #fee2e2; color: #991b1b; }
      .prompt-instructions { color: #93c5fd; margin-top: 8px; }
      .prompt-areas { color: #c4b5fd; }
      .prompt-denoising { color: #a78bfa; }
      
      .expression-badge { display: inline-block; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; margin-left: 8px; }
      .expression-badge.preserve { background: #dbeafe; color: #1e40af; }
      .expression-badge.correct { background: #fef3c7; color: #92400e; }
      .expression-type { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; background: #f3e8ff; color: #6b21a8; }
      .expression-issues { margin-top: 8px; padding: 8px; background: #fef3c7; border-radius: 6px; }
      .expression-issues li { font-size: 12px; color: #92400e; }
      
      .summary-box { background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 16px; }
      .summary-title { font-weight: 600; color: #166534; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
      .summary-text { font-size: 14px; line-height: 1.6; }
      
      .score-bar { height: 8px; background: #e5e7eb; border-radius: 4px; overflow: hidden; margin: 8px 0; }
      .score-fill { height: 100%; border-radius: 4px; transition: width 0.5s; }
      .score-fill.before { background: #f59e0b; }
      .score-fill.after { background: #10b981; }
      
      .loading { display: none; align-items: center; justify-content: center; gap: 12px; padding: 40px; }
      .loading.active { display: flex; }
      .spinner { width: 24px; height: 24px; border: 3px solid #e5e7eb; border-top-color: #4f46e5; border-radius: 50%; animation: spin 1s linear infinite; }
      @keyframes spin { to { transform: rotate(360deg); } }
      
      .error { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 12px; border-radius: 8px; margin-top: 12px; }
      .hidden { display: none !important; }
      
      .step { background: #f9fafb; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
      .step-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
      .step-number { width: 28px; height: 28px; background: #4f46e5; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 14px; font-weight: 600; }
      .step-title { font-weight: 600; font-size: 15px; }
      .step-content { font-size: 14px; line-height: 1.6; }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>🎯 图像真实感增强引擎</h1>
      <p class="subtitle">专家Agent系统：分析AI痕迹 → 路由到专家 → 迭代优化 → 达标输出</p>
      
      <!-- Upload Section -->
      <div class="card">
        <div class="upload-area" id="dropzone">
          <div style="font-size: 48px; margin-bottom: 12px;">📷</div>
          <p>点击上传图片或拖拽到此处</p>
          <p style="font-size: 12px; color: #999; margin-top: 8px;">支持 JPG, PNG, WebP 格式</p>
          <input type="file" id="fileInput" accept="image/*" />
        </div>
        <div class="controls">
          <button id="enhanceBtn" disabled>🚀 专家系统增强</button>
          <button id="analyzeBtn" class="secondary" disabled>📊 仅分析</button>
        </div>
      </div>
      
      <!-- Loading -->
      <div class="loading" id="loading">
        <div class="spinner"></div>
        <span id="loadingText">正在分析图像...</span>
      </div>
      
      <!-- Error Messages -->
      <div id="messageBox"></div>
      
      <!-- Results Section -->
      <div id="results" class="hidden">
        
        <!-- Summary -->
        <div class="card" id="summaryCard">
          <div class="summary-box">
            <div class="summary-title">📋 处理摘要</div>
            <div class="summary-text" id="summaryText"></div>
          </div>
        </div>
        
        <!-- Images Comparison -->
        <div class="card">
          <div class="card-title"><span class="icon">🖼️</span> 图像对比</div>
          <div class="images-row">
            <div class="image-box">
              <div class="image-label">原始图像 (AI痕迹: <span id="initialLikelihood">-</span>)</div>
              <img id="originalImage" alt="原始图像" />
            </div>
            <div class="image-box" id="enhancedBox">
              <div class="image-label">增强后图像 (AI痕迹: <span id="finalLikelihood">-</span>)</div>
              <img id="enhancedImage" alt="增强后图像" />
            </div>
          </div>
        </div>
        
        <!-- Initial Analysis -->
        <div class="card">
          <div class="card-title"><span class="icon">🔍</span> 初始分析</div>
          
          <div class="step">
            <div class="step-header">
              <div class="step-number">1</div>
              <div class="step-title">场景识别</div>
            </div>
            <div class="step-content">
              <div><strong>场景类型：</strong><span class="tag tag-scene" id="sceneType"></span></div>
              <div style="margin-top: 8px;"><strong>场景特征：</strong><span id="sceneAttrs"></span></div>
            </div>
          </div>
          
          <div class="step">
            <div class="step-header">
              <div class="step-number">2</div>
              <div class="step-title">AI痕迹检测</div>
            </div>
            <div class="step-content" id="fakeSignals"></div>
          </div>
        </div>
        
        <!-- Expert Enhancement Iterations -->
        <div class="card" id="iterationsCard">
          <div class="card-title"><span class="icon">🔄</span> 专家迭代过程</div>
          <div id="iterationsContainer"></div>
        </div>
        
        <!-- Raw JSON -->
        <div class="card">
          <div class="card-title"><span class="icon">{ }</span> 原始JSON响应</div>
          <details>
            <summary style="cursor: pointer; color: #666;">点击展开</summary>
            <pre id="rawJson" style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 6px; overflow: auto; max-height: 400px; margin-top: 12px; font-size: 12px;"></pre>
          </details>
        </div>
        
      </div>
    </div>
    
    <script>
      const dropzone = document.getElementById('dropzone');
      const fileInput = document.getElementById('fileInput');
      const enhanceBtn = document.getElementById('enhanceBtn');
      const analyzeBtn = document.getElementById('analyzeBtn');
      const loading = document.getElementById('loading');
      const loadingText = document.getElementById('loadingText');
      const results = document.getElementById('results');
      const messageBox = document.getElementById('messageBox');
      
      let selectedFile = null;
      let originalImageData = null;
      
      const AGENT_ICONS = {
        'skin': '👤',
        'lighting': '💡',
        'texture': '🧱',
        'geometry': '📐',
        'color': '🎨',
        'expression': '😊'
      };
      
      const AGENT_NAMES = {
        'skin': '皮肤专家',
        'lighting': '光线专家',
        'texture': '纹理专家',
        'geometry': '几何专家',
        'color': '色彩专家',
        'expression': '表情专家'
      };
      
      const EXPRESSION_TYPES = {
        'neutral': '中性',
        'big_laugh': '大笑',
        'crying': '大哭',
        'surprise': '惊讶',
        'anger': '愤怒',
        'other': '其他'
      };
      
      // Drag and drop
      dropzone.addEventListener('click', () => fileInput.click());
      dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
      dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
      dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
        if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
      });
      fileInput.addEventListener('change', () => {
        if (fileInput.files.length) handleFile(fileInput.files[0]);
      });
      
      function handleFile(file) {
        if (!file.type.startsWith('image/')) {
          showError('请选择图片文件');
          return;
        }
        selectedFile = file;
        enhanceBtn.disabled = false;
        analyzeBtn.disabled = false;
        
        const reader = new FileReader();
        reader.onload = (e) => {
          originalImageData = e.target.result;
          dropzone.innerHTML = `<img src="${originalImageData}" style="max-height: 200px; border-radius: 8px;" />`;
        };
        reader.readAsDataURL(file);
        
        results.classList.add('hidden');
        messageBox.innerHTML = '';
      }
      
      function showError(text) {
        messageBox.innerHTML = `<div class="error">${text}</div>`;
      }
      
      async function runPipeline(enhance = true) {
        if (!selectedFile) return;
        
        loading.classList.add('active');
        loadingText.textContent = enhance ? '专家系统正在分析和优化图像...' : '正在分析图像...';
        results.classList.add('hidden');
        messageBox.innerHTML = '';
        enhanceBtn.disabled = true;
        analyzeBtn.disabled = true;
        
        const formData = new FormData();
        formData.append('file', selectedFile);
        
        try {
          const endpoint = enhance ? '/enhance' : '/analyze';
          const resp = await fetch(endpoint, { method: 'POST', body: formData });
          const data = await resp.json();
          
          if (!resp.ok) {
            throw new Error(data.detail || '处理失败');
          }
          
          displayResults(data, enhance);
          
        } catch (e) {
          showError(`错误: ${e.message}`);
        } finally {
          loading.classList.remove('active');
          enhanceBtn.disabled = false;
          analyzeBtn.disabled = false;
        }
      }
      
      function displayResults(data, showEnhanced) {
        results.classList.remove('hidden');
        
        // Original image
        document.getElementById('originalImage').src = originalImageData;
        
        // Scene classification
        const sc = data.scene_classification;
        document.getElementById('sceneType').textContent = sc.primary_scene;
        document.getElementById('sceneAttrs').innerHTML = sc.secondary_attributes.map(a => `<span class="tag tag-attr">${a}</span>`).join('');
        document.getElementById('initialLikelihood').textContent = `${(sc.ai_likelihood * 100).toFixed(0)}%`;
        
        // Fake signals
        const fakeSignalsDiv = document.getElementById('fakeSignals');
        if (data.fake_signals && data.fake_signals.length) {
          fakeSignalsDiv.innerHTML = data.fake_signals.map(s => `
            <div class="signal-item">
              <div class="signal-severity ${s.severity}"></div>
              <span>${s.signal}</span>
              <span class="tag tag-${s.severity}" style="margin-left: auto;">${s.severity}</span>
            </div>
          `).join('');
        } else {
          fakeSignalsDiv.innerHTML = '<div style="color: #666;">未检测到明显的AI痕迹</div>';
        }
        
        // Expert enhancement results
        const expertCard = document.getElementById('iterationsCard');
        const summaryCard = document.getElementById('summaryCard');
        const enhancedBox = document.getElementById('enhancedBox');
        
        if (data.expert_enhancement && showEnhanced) {
          const ee = data.expert_enhancement;
          
          // Summary with expression info
          summaryCard.classList.remove('hidden');
          let summaryHtml = ee.summary;
          if (ee.expression_type && ee.expression_type !== 'neutral') {
            const expType = EXPRESSION_TYPES[ee.expression_type] || ee.expression_type;
            const expMode = ee.expression_mode === 'preserve' ? '保留' : '修正';
            summaryHtml += ` <span class="expression-badge ${ee.expression_mode}">${expType}(${expMode})</span>`;
          }
          if (ee.expression_issues && ee.expression_issues.length > 0) {
            summaryHtml += `<div class="expression-issues" style="margin-top: 8px;"><strong>检测到的表情问题：</strong><ul style="margin: 4px 0 0 16px;">${ee.expression_issues.map(i => `<li>${i}</li>`).join('')}</ul></div>`;
          }
          document.getElementById('summaryText').innerHTML = summaryHtml;
          
          // Final likelihood
          document.getElementById('finalLikelihood').textContent = `${(ee.final_ai_likelihood * 100).toFixed(0)}%`;
          
          // Enhanced image
          if (ee.enhanced_image_base64) {
            enhancedBox.classList.remove('hidden');
            let imgData = ee.enhanced_image_base64;
            if (!imgData.startsWith('data:')) {
              imgData = 'data:image/jpeg;base64,' + imgData;
            }
            document.getElementById('enhancedImage').src = imgData;
          } else {
            enhancedBox.classList.add('hidden');
          }
          
          // Iterations
          expertCard.classList.remove('hidden');
          const iterContainer = document.getElementById('iterationsContainer');
          
          if (ee.iterations && ee.iterations.length > 0) {
            iterContainer.innerHTML = ee.iterations.map(it => {
              const improvement = it.ai_likelihood_before - it.ai_likelihood_after;
              const improvementClass = improvement > 0 ? 'improved' : 'same';
              const improvementText = improvement > 0 
                ? `↓ ${(improvement * 100).toFixed(1)}%` 
                : '无变化';
              
              const agentResults = it.agent_results.map(ar => {
                // Render prompt if available
                const p = ar.prompt_used;
                const promptHtml = p ? `
                  <div class="prompt-box">
                    <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px;">
                      <span style="color: #f9fafb; font-weight: 500;">📝 修图提示词</span>
                      <span class="prompt-intensity ${p.intensity}">${p.intensity === 'light' ? '轻度' : p.intensity === 'medium' ? '中度' : '强度'}</span>
                      ${p.expression_mode ? `<span class="expression-badge ${p.expression_mode}">${p.expression_mode === 'preserve' ? '🔒 表情保留' : '🔧 表情修正'}</span>` : ''}
                      ${p.denoising_strength ? `<span style="color: #a78bfa; font-size: 11px;">降噪: ${p.denoising_strength}</span>` : ''}
                    </div>
                    ${p.preservation_prompt ? `
                      <div class="prompt-section">
                        <div class="prompt-label">🔒 保留约束 (Preservation)</div>
                        <div class="prompt-preservation">${p.preservation_prompt}</div>
                      </div>
                    ` : ''}
                    ${p.correction_prompt && p.expression_mode === 'correct' ? `
                      <div class="prompt-section">
                        <div class="prompt-label">🔧 修正指导 (Correction)</div>
                        <div class="prompt-correction">${p.correction_prompt}</div>
                      </div>
                    ` : ''}
                    <div class="prompt-section">
                      <div class="prompt-label">✅ 正向提示词 (Positive)</div>
                      <div class="prompt-positive">${p.positive_prompt || '无'}</div>
                    </div>
                    <div class="prompt-section">
                      <div class="prompt-label">❌ 负向提示词 (Negative)</div>
                      <div class="prompt-negative">${p.negative_prompt || '无'}</div>
                    </div>
                    ${p.specific_instructions && p.specific_instructions.length > 0 ? `
                      <div class="prompt-section">
                        <div class="prompt-label">📋 具体指令</div>
                        <div class="prompt-instructions">${p.specific_instructions.join(' | ')}</div>
                      </div>
                    ` : ''}
                    ${p.target_areas && p.target_areas.length > 0 ? `
                      <div class="prompt-section">
                        <div class="prompt-label">🎯 目标区域</div>
                        <div class="prompt-areas">${p.target_areas.join(', ')}</div>
                      </div>
                    ` : ''}
                    ${p.expression_type && p.expression_type !== 'neutral' ? `
                      <div class="prompt-section">
                        <div class="prompt-label">😊 表情类型</div>
                        <span class="expression-type">${EXPRESSION_TYPES[p.expression_type] || p.expression_type}</span>
                      </div>
                    ` : ''}
                    ${p.expression_issues && p.expression_issues.length > 0 ? `
                      <div class="prompt-section">
                        <div class="prompt-label">⚠️ 表情问题</div>
                        <ul style="margin: 4px 0 0 16px; padding: 0; color: #fbbf24;">
                          ${p.expression_issues.map(i => `<li style="font-size: 11px;">${i}</li>`).join('')}
                        </ul>
                      </div>
                    ` : ''}
                  </div>
                ` : '';
                
                return `
                  <div class="agent-result">
                    <div class="agent-header">
                      <div class="agent-icon ${ar.agent_type}">${AGENT_ICONS[ar.agent_type] || '🔧'}</div>
                      <span class="agent-name">${AGENT_NAMES[ar.agent_type] || ar.agent_type}</span>
                      <span class="tag ${ar.success ? 'tag-low' : 'tag-high'}" style="margin-left: auto;">
                        ${ar.success ? '✓ 成功' : '✗ 失败'}
                      </span>
                    </div>
                    <div style="font-size: 13px; color: #666;">${ar.description}</div>
                    ${ar.changes_made && ar.changes_made.length > 0 ? `
                      <ul class="agent-changes">
                        ${ar.changes_made.map(c => `<li>${c}</li>`).join('')}
                      </ul>
                    ` : ''}
                    ${promptHtml}
                  </div>
                `;
              }).join('');
              
              return `
                <div class="iteration-card">
                  <div class="iteration-header">
                    <span class="iteration-number">第 ${it.iteration} 轮迭代</span>
                    <span class="iteration-likelihood">
                      AI痕迹: ${(it.ai_likelihood_before * 100).toFixed(0)}% → ${(it.ai_likelihood_after * 100).toFixed(0)}%
                      <span class="likelihood-change ${improvementClass}">(${improvementText})</span>
                    </span>
                  </div>
                  <div style="font-size: 13px; color: #666; margin-bottom: 12px;">
                    <strong>路由决策：</strong>${it.routing_reasoning}
                  </div>
                  <div>
                    <strong>调用专家：</strong>
                    ${it.agents_invoked.map(a => `<span class="tag tag-agent">${AGENT_ICONS[a] || ''} ${AGENT_NAMES[a] || a}</span>`).join('')}
                  </div>
                  ${agentResults}
                </div>
              `;
            }).join('');
          } else {
            iterContainer.innerHTML = '<div style="color: #666; padding: 12px;">AI痕迹较低，无需迭代优化</div>';
          }
          
        } else {
          summaryCard.classList.add('hidden');
          expertCard.classList.add('hidden');
          enhancedBox.classList.add('hidden');
          document.getElementById('finalLikelihood').textContent = '-';
        }
        
        // Raw JSON
        document.getElementById('rawJson').textContent = JSON.stringify(data, null, 2);
      }
      
      enhanceBtn.addEventListener('click', () => runPipeline(true));
      analyzeBtn.addEventListener('click', () => runPipeline(false));
    </script>
  </body>
</html>
""".strip()
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "realism-enhancement-engine"}


@router.post("/upload", response_model=UploadResponse)
async def upload_image(file: UploadFile = File(...)):
    """Upload an image for processing."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    content = await file.read()

    if len(content) > settings.max_image_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size // 1024 // 1024}MB."
        )

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    job_id = str(uuid.uuid4())
    storage_path = Path(settings.storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)

    file_path = storage_path / f"{job_id}.jpg"
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    jobs[job_id] = {
        "status": JobStatus.PENDING,
        "file_path": str(file_path),
        "result": None,
        "error": None,
    }

    return UploadResponse(job_id=job_id, message="Image uploaded successfully")


@router.post("/process/{job_id}", response_model=JobResponse)
async def process_image(job_id: str, background_tasks: BackgroundTasks):
    """Start processing an uploaded image."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]

    if job["status"] == JobStatus.PROCESSING:
        return JobResponse(job_id=job_id, status=JobStatus.PROCESSING, result=None, error=None)

    if job["status"] == JobStatus.COMPLETED:
        return JobResponse(job_id=job_id, status=JobStatus.COMPLETED, result=job["result"], error=None)

    job["status"] = JobStatus.PROCESSING
    background_tasks.add_task(run_pipeline, job_id)

    return JobResponse(job_id=job_id, status=JobStatus.PROCESSING, result=None, error=None)


async def run_pipeline(job_id: str):
    """Run the enhancement pipeline for a job."""
    job = jobs[job_id]

    try:
        async with aiofiles.open(job["file_path"], "rb") as f:
            image_data = await f.read()

        image_base64 = base64.b64encode(image_data).decode("utf-8")

        orchestrator = get_orchestrator()
        result = await orchestrator.process(image_base64)

        job["status"] = JobStatus.COMPLETED
        job["result"] = result

    except Exception as e:
        job["status"] = JobStatus.FAILED
        job["error"] = str(e)


@router.get("/result/{job_id}", response_model=JobResponse)
async def get_result(job_id: str):
    """Get the result of a processed image."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return JobResponse(job_id=job_id, status=job["status"], result=job["result"], error=job["error"])


@router.post("/analyze")
async def analyze_image_only(file: UploadFile = File(...)):
    """Analyze an image without enhancement."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    content = await file.read()

    if len(content) > settings.max_image_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size // 1024 // 1024}MB."
        )

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    image_base64 = base64.b64encode(content).decode("utf-8")

    orchestrator = get_orchestrator()
    result = await orchestrator.analyze_only(image_base64)

    return result


@router.post("/enhance")
async def enhance_image(file: UploadFile = File(...)):
    """Analyze and enhance an image using the expert agent system."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")

    content = await file.read()

    if len(content) > settings.max_image_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {settings.max_image_size // 1024 // 1024}MB."
        )

    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    image_base64 = base64.b64encode(content).decode("utf-8")

    orchestrator = get_orchestrator()
    result = await orchestrator.process(image_base64, enhance_image=True, use_expert_system=True)

    return result
