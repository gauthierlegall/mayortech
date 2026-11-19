// Copyright (c) 2022-present TOEVERYTHING PTE. LTD. and its affiliates.
// SPDX-License-Identifier: MIT
// Exact function excerpt; provenance.json records source and SHA. Only type import added.
import type {DatabaseBlockDataSource} from "@blocksuite/affine/blocks/database";

export const databaseViewInitTemplate = (
  datasource: DatabaseBlockDataSource,
  viewType: string
) => {
  Array.from({ length: 3 }).forEach(() => {
    datasource.rowAdd('end');
  });
  datasource.viewManager.viewAdd(viewType);
};
