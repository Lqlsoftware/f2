import pytest
from f2.apps.tiktok.utils import TokenManager

def test_gen_real_msToken():
    token = TokenManager.gen_real_msToken()
    assert token is not None, "gen_real_msToken() should return a valid token"
    assert isinstance(token, str), "gen_real_msToken() should return a string"

def test_gen_false_msToken():
    token = TokenManager.gen_false_msToken()
    assert token is not None, "gen_false_msToken() should return a valid token"
    assert isinstance(token, str), "gen_false_msToken() should return a string"

def test_gen_ttwid():
    ttwid = TokenManager.gen_ttwid()
    assert ttwid is not None, "gen_ttwid() should return a valid ttwid"
    assert isinstance(ttwid, str), "gen_ttwid() should return a string"

def test_gen_odin_tt():
    csrf_token = TokenManager.gen_odin_tt()
    assert csrf_token is not None, "gen_odin_tt() should return a valid csrf token"
    assert isinstance(csrf_token, str), "gen_odin_tt() should return a string"