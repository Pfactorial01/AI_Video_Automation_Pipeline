// Build row fields for Google Sheets "Update Row" (auto-map). Match on the real column **sheet_row**
// (=ROW() value). Do not use n8n's virtual "row_number" match unless a column named row_number exists.
const pipeline = $input.first().json;
const cfg = $('Pipeline config').first().json;

const rowNum = Number(cfg.row_number ?? cfg.sheet_row);
if (!Number.isFinite(rowNum) || rowNum < 2) {
  throw new Error(
    'Add a column sheet_row with =ROW() on each data row (see templates/google_sheet_columns.csv). The rowAdded trigger does not include row numbers; =ROW() gives the row to update.',
  );
}

return [
  {
    json: {
      sheet_row: rowNum,
      status: 'COMPLETE',
      output_mp4_url: pipeline.final_mp4_url ?? '',
      voice_url: pipeline.voice_url ?? '',
      script_json_url: '',
      error_message: '',
      n8n_execution_url: '',
    },
  },
];
