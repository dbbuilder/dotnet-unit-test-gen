#!/bin/bash
# Example usage scenarios for .NET Unit Test Generator

# Ensure virtual environment is activated
if [ ! -d "venv" ]; then
    echo "❌ Run ./setup.sh first"
    exit 1
fi

source venv/bin/activate

echo "📚 .NET Unit Test Generator - Example Usage"
echo "============================================"
echo ""

# Example 1: Dry run
echo "Example 1: Dry run (analyze only, no generation)"
echo "Command: python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api --dry-run"
echo ""
# Uncomment to run:
# python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api --dry-run

# Example 2: Generate tests for controllers only
echo "Example 2: Generate tests for Controllers only (limited to 5)"
echo "Command: python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api -p 'Controller' -n 5"
echo ""
# Uncomment to run:
# python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api \
#     -o /mnt/d/dev2/remotec/tests/RemoteC.Api.Tests \
#     -p "Controller" \
#     -n 5

# Example 3: Generate tests for services
echo "Example 3: Generate tests for Services"
echo "Command: python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Host -p 'Service'"
echo ""
# Uncomment to run:
# python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Host \
#     -o /mnt/d/dev2/remotec/tests/RemoteC.Host.Tests \
#     -p "Service"

# Example 4: Generate tests for specific class
echo "Example 4: Generate tests for a specific class"
echo "Command: python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api -p 'SessionsController'"
echo ""
# Uncomment to run:
# python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api \
#     -o /mnt/d/dev2/remotec/tests/RemoteC.Api.Tests \
#     -p "SessionsController"

# Example 5: Force regenerate existing tests
echo "Example 5: Force regenerate existing tests"
echo "Command: python generate_tests.py /path/to/project --force"
echo ""
# Uncomment to run:
# python generate_tests.py /mnt/d/dev2/remotec/src/RemoteC.Api \
#     -o /mnt/d/dev2/remotec/tests/RemoteC.Api.Tests \
#     --force

echo ""
echo "💡 Tip: Uncomment the examples above to run them"
echo "💡 Tip: Always start with --dry-run to preview what will be generated"
echo ""
