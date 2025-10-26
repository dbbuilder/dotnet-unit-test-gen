#!/bin/bash
# Test script for LangChain-enhanced generator on RemoteC

set -e

echo "========================================="
echo "LangChain Enhanced Generator - RemoteC Test"
echo "========================================="
echo ""

cd /mnt/d/dev2/dotnet-unit-test-gen
source venv/bin/activate

# Test 1: Single controller (quick validation)
echo "Test 1: Single Controller (DevicesController)"
echo "----------------------------------------------"
python generate_tests_enhanced.py \
  /mnt/d/dev2/remotec/src/RemoteC.Api \
  -o /tmp/test-langchain-single \
  -p "^DevicesController$" \
  --use-context \
  --auto-learn \
  --auto-refine \
  --force

echo ""
echo "✓ Test 1 Complete"
echo ""

# Test 2: Small batch (3 controllers)
echo "Test 2: Small Batch (3 Controllers)"
echo "------------------------------------"
python generate_tests_enhanced.py \
  /mnt/d/dev2/remotec/src/RemoteC.Api \
  -o /tmp/test-langchain-batch \
  -p "^(Devices|Sessions|Dashboard)Controller$" \
  --use-context \
  --auto-learn \
  --auto-refine \
  --force

echo ""
echo "✓ Test 2 Complete"
echo ""

# Test 3: Full run (all 44 controllers) - OPTIONAL
read -p "Run full test on all 44 controllers? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Test 3: Full Project (All Controllers)"
    echo "---------------------------------------"
    python generate_tests_enhanced.py \
      /mnt/d/dev2/remotec/src/RemoteC.Api \
      -o /tmp/test-langchain-full \
      -p ".*Controller$" \
      --use-context \
      --auto-learn \
      --auto-refine \
      --force

    echo ""
    echo "✓ Test 3 Complete"
    echo ""
fi

echo "========================================="
echo "All Tests Complete!"
echo "========================================="
echo ""
echo "Results:"
echo "  - Test 1: /tmp/test-langchain-single"
echo "  - Test 2: /tmp/test-langchain-batch"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  - Test 3: /tmp/test-langchain-full"
fi
echo ""
echo "Review session reports in each directory for details."
