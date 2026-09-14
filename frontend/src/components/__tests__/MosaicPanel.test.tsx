import React from 'react';
import { describe, it, expect } from 'vitest';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { MosaicPanel } from '../MosaicPanel';
import type { MosaicResult } from '../../types';

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe('MosaicPanel component', () => {
  it('renders clean state when zero convergences are found', async () => {
    const emptyResult: MosaicResult = {
      convergences: [],
      mosaic_score: 0.0,
      file_count: 2,
      error: null,
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(<MosaicPanel result={emptyResult} />);
    });

    expect(container.textContent).toContain('No Cross-File Convergences Detected');
    expect(container.textContent).toContain('0.0');
    expect(container.textContent).toContain('Isolated Batch Exposure');

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  it('renders convergence cards, score, and linked files when risk is detected', async () => {
    const populatedResult: MosaicResult = {
      convergences: [
        {
          entity_type: 'ORG',
          representative_text: 'Acme Corp',
          source_files: ['contract.pdf', 'invoice.pdf'],
          priority: 'low',
          explanation: "'Acme Corp' (ORG) appears across contract.pdf, invoice.pdf.",
        },
        {
          entity_type: 'LOCATION_PROXIMITY',
          representative_text: 'Geo proximity (0.42 km)',
          source_files: ['photo1.jpg', 'photo2.jpg'],
          priority: 'high',
          explanation: 'Geographic coordinates in photo1.jpg (EXIF GPS) and photo2.jpg (GeoCLIP) are within 0.42 km of each other.',
        },
      ],
      mosaic_score: 8.0,
      file_count: 3,
      error: null,
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(<MosaicPanel result={populatedResult} />);
    });

    expect(container.textContent).toContain('Layer C — Mosaic Risk Analysis');
    expect(container.textContent).toContain('8.0');
    expect(container.textContent).toContain('High Mosaic Exposure');
    expect(container.textContent).toContain('Acme Corp');
    expect(container.textContent).toContain('Geo proximity (0.42 km)');
    expect(container.textContent).toContain('contract.pdf');
    expect(container.textContent).toContain('invoice.pdf');
    expect(container.textContent).toContain('photo1.jpg');
    expect(container.textContent).toContain('photo2.jpg');

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });

  it('renders possible associations section when present and omits it when empty', async () => {
    const withAssocResult: MosaicResult = {
      convergences: [],
      possible_associations: [
        {
          person_text: 'Jane Doe',
          org_text: 'TechCorp',
          org_filename: 'company_memo.pdf',
          explanation: "Jane Doe is the only identified individual in this batch; 'TechCorp' appears separately in company_memo.pdf.",
          confidence_label: 'low',
        },
      ],
      mosaic_score: 0.0,
      file_count: 2,
      error: null,
    };

    const container = document.createElement('div');
    document.body.appendChild(container);
    const root = createRoot(container);

    await act(async () => {
      root.render(<MosaicPanel result={withAssocResult} />);
    });

    expect(container.textContent).toContain('Possible Associations (unconfirmed)');
    expect(container.textContent).toContain('Jane Doe');
    expect(container.textContent).toContain('TechCorp');
    expect(container.textContent).toContain('company_memo.pdf');
    expect(container.textContent).toContain('low confidence');

    await act(async () => {
      root.unmount();
    });
    container.remove();
  });
});

