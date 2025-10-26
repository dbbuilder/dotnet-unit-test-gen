#!/usr/bin/env python3
"""
Regenerate EcommerceDataAccess test with improved mocking using GPT-4o Mini
"""
import os
import sys
from pathlib import Path

# Set model to GPT-4o Mini before importing
os.environ['PRIMARY_MODEL'] = 'gpt-4o-mini'

from generate_tests_vbnet import TestGenerator, TestStats, ProjectPatternCache, ClassInfo

# Create instances
stats = TestStats()
project_dir = Path('/mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentDataAccess')
pattern_cache = ProjectPatternCache(project_dir)
generator = TestGenerator(stats, project_dir, pattern_cache)

# Read source file
source_file = Path('/mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentDataAccess/EcommerceDataAccess.vb')
source_code = source_file.read_text()

# Create ClassInfo
class_info = ClassInfo(
    name='LookupProductsEcommerceRequest',
    namespace='PaymentDataAccess',
    file_path=source_file,
    source_code=source_code[:8000],  # Truncate for token limit
    methods=['BuildSQLParameters', 'MapDataReaderToModel'],
    dependencies=['DataAccessRequestBase', 'IDataReader', 'SqlParameter'],
    is_controller=False,
    is_service=False,
    language='vbnet'
)

# Generate test
print('Generating test with GPT-4o Mini...')
print(f'Model: {os.getenv("PRIMARY_MODEL")}')
test_code = generator.generate_tests_for_class(class_info)

# Write output
output_file = Path('/mnt/d/Dev2/michaeljr/PaymentAPI-original/PaymentAPI.Tests.Unit/DataAccess/LookupProductsEcommerceRequestTests_New.vb')
output_file.write_text(test_code)

print(f'\nGenerated test: {output_file}')
print(f'Tokens used: {stats.tokens_used}')
print(f'Cost: ${stats.cost_usd:.4f}')
print(f'\nTest generation complete!')
