"""Tests for context matching functionality"""

from app.core.prompts.context_matcher import ContextMatcher


class TestContextMatcher:
    """Test the generic context matching system"""

    def setup_method(self):
        """Set up test fixtures"""
        self.matcher = ContextMatcher()

    def test_empty_fragment_context_matches_all(self):
        """Empty fragment context should match any runtime context"""
        fragment_context = {}
        runtime_context = {"state": "NSW", "contract_type": "purchase"}

        assert self.matcher.matches_context(fragment_context, runtime_context) is True

    def test_wildcard_matches_any_value(self):
        """Wildcard (*) should match any value"""
        fragment_context = {"state": "*", "contract_type": "*"}
        runtime_context = {"state": "NSW", "contract_type": "purchase"}

        assert self.matcher.matches_context(fragment_context, runtime_context) is True

    def test_exact_string_match_case_insensitive(self):
        """Exact string values should match case-insensitively"""
        fragment_context = {"state": "NSW"}

        # Exact match
        assert self.matcher.matches_context(fragment_context, {"state": "NSW"}) is True

        # Case insensitive
        assert self.matcher.matches_context(fragment_context, {"state": "nsw"}) is True
        assert self.matcher.matches_context(fragment_context, {"state": "Nsw"}) is True

        # No match
        assert self.matcher.matches_context(fragment_context, {"state": "VIC"}) is False

    def test_list_matching_case_insensitive(self):
        """List values should match if runtime value is in list (case-insensitive)"""
        fragment_context = {"contract_type": ["purchase", "option"]}

        # In list
        assert (
            self.matcher.matches_context(
                fragment_context, {"contract_type": "purchase"}
            )
            is True
        )
        assert (
            self.matcher.matches_context(fragment_context, {"contract_type": "option"})
            is True
        )

        # Case insensitive
        assert (
            self.matcher.matches_context(
                fragment_context, {"contract_type": "PURCHASE"}
            )
            is True
        )
        assert (
            self.matcher.matches_context(fragment_context, {"contract_type": "Option"})
            is True
        )

        # Not in list
        assert (
            self.matcher.matches_context(fragment_context, {"contract_type": "lease"})
            is False
        )

    def test_missing_runtime_key_fails_match(self):
        """Missing runtime context key should fail match (unless fragment value is wildcard)"""
        fragment_context = {"state": "NSW", "contract_type": "purchase"}
        runtime_context = {"state": "NSW"}  # Missing contract_type

        assert self.matcher.matches_context(fragment_context, runtime_context) is False

    def test_missing_runtime_key_with_wildcard_passes(self):
        """Missing runtime context key with wildcard fragment value should pass"""
        fragment_context = {"state": "NSW", "contract_type": "*"}
        runtime_context = {"state": "NSW"}  # Missing contract_type

        assert self.matcher.matches_context(fragment_context, runtime_context) is True

    def test_complex_context_matching(self):
        """Test complex context with multiple conditions"""
        fragment_context = {
            "state": "NSW",
            "contract_type": ["purchase", "option"],
            "user_experience": "*",
            "analysis_depth": "comprehensive",
        }

        # All match
        runtime_context = {
            "state": "NSW",
            "contract_type": "purchase",
            "user_experience": "novice",
            "analysis_depth": "comprehensive",
        }
        assert self.matcher.matches_context(fragment_context, runtime_context) is True

        # State mismatch
        runtime_context["state"] = "VIC"
        assert self.matcher.matches_context(fragment_context, runtime_context) is False

        # Contract type not in list
        runtime_context["state"] = "NSW"
        runtime_context["contract_type"] = "lease"
        assert self.matcher.matches_context(fragment_context, runtime_context) is False

        # Analysis depth mismatch
        runtime_context["contract_type"] = "purchase"
        runtime_context["analysis_depth"] = "quick"
        assert self.matcher.matches_context(fragment_context, runtime_context) is False

    def test_filter_fragments(self):
        """Test filtering fragments based on context"""
        fragments = [
            {
                "name": "nsw_purchase",
                "content": "NSW purchase content",
                "metadata": {"context": {"state": "NSW", "contract_type": "purchase"}},
            },
            {
                "name": "nsw_any_contract",
                "content": "NSW any contract content",
                "metadata": {"context": {"state": "NSW", "contract_type": "*"}},
            },
            {
                "name": "vic_purchase",
                "content": "VIC purchase content",
                "metadata": {"context": {"state": "VIC", "contract_type": "purchase"}},
            },
            {"name": "no_context", "content": "No context content", "metadata": {}},
        ]

        runtime_context = {"state": "NSW", "contract_type": "purchase"}

        matching = self.matcher.filter_fragments(fragments, runtime_context)
        matching_names = [f["name"] for f in matching]

        # Should match NSW purchase, NSW any contract, and no context
        assert "nsw_purchase" in matching_names
        assert "nsw_any_contract" in matching_names
        assert "no_context" in matching_names
        assert "vic_purchase" not in matching_names

        assert len(matching) == 3

    def test_non_string_values(self):
        """Test handling of non-string values"""
        fragment_context = {"priority": 80, "enabled": True}
        runtime_context = {"priority": 80, "enabled": True}

        assert self.matcher.matches_context(fragment_context, runtime_context) is True

        # Different values
        runtime_context = {"priority": 90, "enabled": False}
        assert self.matcher.matches_context(fragment_context, runtime_context) is False
