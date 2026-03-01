import React, { useState, useMemo } from 'react';
import {
  Box, Typography, Button, Chip, Paper, Divider,
  Tooltip, IconButton, Collapse, Alert
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ReceiptIcon from '@mui/icons-material/Receipt';
import NoteAltIcon from '@mui/icons-material/NoteAlt';
import ArticleIcon from '@mui/icons-material/Article';

// Tags that indicate a text-heavy image
const TEXT_INDICATOR_TAGS = [
  'receipt', 'invoice', 'bill', 'document', 'note', 'notes',
  'handwritten', 'handwriting', 'paper', 'book', 'page',
  'letter', 'sign', 'label', 'poster', 'menu', 'form',
  'text', 'writing', 'whiteboard', 'blackboard', 'screenshot',
  'certificate', 'card', 'ticket', 'newspaper', 'magazine'
];

const DOC_TYPE_MAP = {
  receipt: { label: 'Receipt', icon: <ReceiptIcon fontSize="small" /> },
  invoice: { label: 'Invoice', icon: <ReceiptIcon fontSize="small" /> },
  bill:    { label: 'Bill',    icon: <ReceiptIcon fontSize="small" /> },
  note:    { label: 'Note',    icon: <NoteAltIcon fontSize="small" /> },
  notes:   { label: 'Notes',   icon: <NoteAltIcon fontSize="small" /> },
  handwritten: { label: 'Handwritten', icon: <NoteAltIcon fontSize="small" /> },
};

/**
 * Reconstruct spatially-aware text from EasyOCR bounding-box regions.
 *
 * bbox format: [[x1,y1],[x2,y2],[x3,y3],[x4,y4]] (TL→TR→BR→BL)
 * Strategy:
 *   1. Sort regions top→bottom by centre-Y.
 *   2. Group into "lines" when vertical gap > lineHeight * 0.6.
 *   3. Within each line sort left→right by centre-X.
 *   4. Estimate column positions to add spacing between words.
 */
function buildAlignedText(regions) {
  if (!regions || regions.length === 0) return '';

  const withMeta = regions.map(r => {
    const xs = r.bbox.map(p => p[0]);
    const ys = r.bbox.map(p => p[1]);
    const x1 = Math.min(...xs), x2 = Math.max(...xs);
    const y1 = Math.min(...ys), y2 = Math.max(...ys);
    return {
      text: r.text,
      confidence: r.confidence,
      cx: (x1 + x2) / 2,
      cy: (y1 + y2) / 2,
      x1, x2, y1, y2,
      h: y2 - y1,
    };
  });

  // Sort top→bottom
  withMeta.sort((a, b) => a.cy - b.cy);

  // Average line height to set grouping threshold
  const avgH = withMeta.reduce((s, r) => s + r.h, 0) / withMeta.length;
  const lineThreshold = avgH * 0.7;

  // Group into lines
  const lines = [];
  let currentLine = [withMeta[0]];

  for (let i = 1; i < withMeta.length; i++) {
    const prev = currentLine[currentLine.length - 1];
    if (Math.abs(withMeta[i].cy - prev.cy) <= lineThreshold) {
      currentLine.push(withMeta[i]);
    } else {
      lines.push(currentLine);
      currentLine = [withMeta[i]];
    }
  }
  lines.push(currentLine);

  // Find the global x-range to normalise indentation
  const globalX1 = Math.min(...withMeta.map(r => r.x1));
  const globalX2 = Math.max(...withMeta.map(r => r.x2));
  const totalWidth = globalX2 - globalX1 || 1;
  // Approximate: 80 chars across the full width
  const charsPerPixel = 80 / totalWidth;

  return lines.map(line => {
    // Sort left→right
    line.sort((a, b) => a.x1 - b.x1);

    let result = '';
    let cursorX = globalX1;

    line.forEach(word => {
      // Spaces to simulate indentation/gap
      const gap = Math.round((word.x1 - cursorX) * charsPerPixel);
      const spaces = Math.max(gap > 2 ? gap : 1, 1); // always at least 1 space
      result += ' '.repeat(spaces) + word.text;
      cursorX = word.x2;
    });

    return result;
  }).join('\n');
}

/**
 * Detect document type from image tags and OCR text content.
 */
function detectDocType(tags, ocrText) {
  const tagLower = (tags || []).map(t => t.toLowerCase());
  const textLower = (ocrText || '').toLowerCase();

  for (const [key, val] of Object.entries(DOC_TYPE_MAP)) {
    if (tagLower.some(t => t.includes(key)) || textLower.includes(key)) {
      return val;
    }
  }
  return { label: 'Document', icon: <ArticleIcon fontSize="small" /> };
}

/**
 * Decide whether to show the OCR panel at all.
 * Show if: has ocr_text with meaningful content, OR tags suggest text.
 */
export function shouldShowOCR(img) {
  if (!img) return false;
  const ocrText = img.ocr_text || '';
  if (ocrText.trim().length > 5) return true;

  const tagNames = (img.tags || [])
    .map(t => (typeof t === 'string' ? t : t.tag_name || t.label || '').toLowerCase());
  return tagNames.some(t => TEXT_INDICATOR_TAGS.some(kw => t.includes(kw)));
}

export default function OCRTextViewer({ img }) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const ocrText = img?.ocr_text || '';
  const ocrRegions = img?.ocr_regions || [];
  const tags = (img?.tags || []).map(t =>
    typeof t === 'string' ? t : t.tag_name || t.label || ''
  );

  const hasOCR = ocrText.trim().length > 5;
  const docType = useMemo(() => detectDocType(tags, ocrText), [tags, ocrText]);

  // Build spatially-aligned text if we have region data; fall back to raw text
  const alignedText = useMemo(() => {
    if (ocrRegions.length > 0) return buildAlignedText(ocrRegions);
    return ocrText;
  }, [ocrRegions, ocrText]);

  const handleCopy = () => {
    navigator.clipboard.writeText(alignedText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  if (!hasOCR && !shouldShowOCR(img)) return null;

  return (
    <Box sx={{ mt: 2.5 }}>
      <Divider sx={{ mb: 2 }} />

      {/* Header row */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <TextSnippetIcon sx={{ color: 'primary.main', fontSize: 20 }} />
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'primary.main', flexGrow: 1 }}>
          Text Extraction (OCR)
        </Typography>
        <Chip
          icon={docType.icon}
          label={docType.label}
          size="small"
          color="primary"
          variant="outlined"
          sx={{ fontSize: '0.7rem' }}
        />
      </Box>

      {!hasOCR ? (
        /* No text found yet */
        <Alert severity="info" sx={{ borderRadius: 2, py: 0.5 }}>
          {img?.status === 'completed'
            ? 'No readable text was detected in this image.'
            : 'OCR processing in progress…'}
        </Alert>
      ) : (
        <>
          {/* Collapsed preview — first line */}
          <Paper
            variant="outlined"
            sx={{
              borderRadius: 2,
              overflow: 'hidden',
              borderColor: 'primary.light',
            }}
          >
            {/* Toolbar */}
            <Box
              sx={{
                px: 2, py: 1,
                bgcolor: 'primary.50',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: expanded ? '1px solid' : 'none',
                borderColor: 'divider',
                background: 'linear-gradient(90deg, #e3f2fd 0%, #f3f8ff 100%)',
              }}
            >
              <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                {ocrRegions.length > 0
                  ? `${ocrRegions.length} text region${ocrRegions.length !== 1 ? 's' : ''} detected`
                  : 'Text detected'}
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <Tooltip title={copied ? 'Copied!' : 'Copy all text'}>
                  <IconButton size="small" onClick={handleCopy} color={copied ? 'success' : 'default'}>
                    {copied ? <CheckIcon fontSize="small" /> : <ContentCopyIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
                <Tooltip title={expanded ? 'Collapse' : 'Expand'}>
                  <IconButton size="small" onClick={() => setExpanded(v => !v)}>
                    {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>

            {/* Preview (always visible — first 3 lines) */}
            <Box sx={{ px: 2, pt: 1.5, pb: expanded ? 0 : 1.5 }}>
              <Typography
                component="pre"
                sx={{
                  fontFamily: '"Courier New", Courier, monospace',
                  fontSize: '0.78rem',
                  lineHeight: 1.7,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  color: 'text.primary',
                  m: 0,
                  display: '-webkit-box',
                  WebkitLineClamp: expanded ? 'unset' : 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: expanded ? 'visible' : 'hidden',
                }}
              >
                {alignedText}
              </Typography>
            </Box>

            {/* Full expanded text */}
            <Collapse in={expanded}>
              <Box sx={{ px: 2, pb: 2 }}>
                {/* Word-confidence breakdown */}
                {ocrRegions.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" sx={{ color: 'text.secondary', fontWeight: 600 }}>
                      Word confidence:
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                      {ocrRegions.map((r, i) => (
                        <Chip
                          key={i}
                          label={r.text}
                          size="small"
                          sx={{
                            fontSize: '0.68rem',
                            height: 22,
                            bgcolor: r.confidence >= 0.8
                              ? '#e8f5e9'  // green — high confidence
                              : r.confidence >= 0.5
                                ? '#fff3e0'  // amber — medium
                                : '#fce4ec', // red — low
                            color: r.confidence >= 0.8
                              ? '#2e7d32'
                              : r.confidence >= 0.5
                                ? '#e65100'
                                : '#c62828',
                            border: '1px solid',
                            borderColor: r.confidence >= 0.8
                              ? '#a5d6a7'
                              : r.confidence >= 0.5
                                ? '#ffcc80'
                                : '#ef9a9a',
                          }}
                        />
                      ))}
                    </Box>
                    <Typography variant="caption" sx={{ color: 'text.disabled', display: 'block', mt: 0.5 }}>
                      Green = high confidence · Amber = medium · Red = low
                    </Typography>
                  </Box>
                )}
              </Box>
            </Collapse>
          </Paper>

          {/* Copy button below */}
          <Box sx={{ mt: 1, display: 'flex', justifyContent: 'flex-end' }}>
            <Button
              size="small"
              variant={copied ? 'contained' : 'outlined'}
              color={copied ? 'success' : 'primary'}
              startIcon={copied ? <CheckIcon /> : <ContentCopyIcon />}
              onClick={handleCopy}
              sx={{ borderRadius: 2, textTransform: 'none', fontSize: '0.75rem' }}
            >
              {copied ? 'Copied!' : 'Copy Text'}
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
}