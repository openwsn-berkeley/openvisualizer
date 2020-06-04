"""
# Copyright (c) 2010-2020, Regents of the University of California.
# All rights reserved.
#
# Released under the BSD 3-Clause license as published at the link below.
# https://openwsn.atlassian.net/wiki/display/OW/License
"""

from enum import IntEnum


class CoJPLabel(IntEnum):
    COJP_PARAMETERS_LABELS_ROLE = 1  # Identifies the role parameter
    COJP_PARAMETERS_LABELS_LLKEYSET = 2  # Identifies the array carrying one or more link-layer cryptographic keys
    COJP_PARAMETERS_LABELS_LLSHORTADDRESS = 3  # Identifies the assigned link-layer short address
    COJP_PARAMETERS_LABELS_JRCADDRESS = 4  # Identifies the IPv6 address of the jrc
    COJP_PARAMETERS_LABELS_NETID = 5  # Identifies the network identifier (PAN ID)
    COJP_PARAMETERS_LABELS_NETPREFIX = 6  # Identifies the IPv6 prefix of the network


class CoJPRole(IntEnum):
    COJP_ROLE_6N = 0  # 6TiSCH Node
    COJP_ROLE_6LBR = 1  # 6LBR Node


class CoJPKeyUsage(IntEnum):
    COJP_KEY_USAGE_6TiSCH_K1K2_ENC_MIC32 = 0
    COJP_KEY_USAGE_6TiSCH_K1K2_ENC_MIC64 = 1
    COJP_KEY_USAGE_6TiSCH_K1K2_ENC_MIC128 = 2
    COJP_KEY_USAGE_6TiSCH_K1K2_MIC32 = 3
    COJP_KEY_USAGE_6TiSCH_K1K2_MIC64 = 4
    COJP_KEY_USAGE_6TiSCH_K1K2_MIC128 = 5
    COJP_KEY_USAGE_6TiSCH_K1_MIC32 = 6
    COJP_KEY_USAGE_6TiSCH_K1_MIC64 = 7
    COJP_KEY_USAGE_6TiSCH_K1_MIC128 = 8
    COJP_KEY_USAGE_6TiSCH_K2_MIC32 = 9
    COJP_KEY_USAGE_6TiSCH_K2_MIC64 = 10
    COJP_KEY_USAGE_6TiSCH_K2_MIC128 = 11
    COJP_KEY_USAGE_6TiSCH_K2_ENC_MIC32 = 12
    COJP_KEY_USAGE_6TiSCH_K2_ENC_MIC64 = 13
    COJP_KEY_USAGE_6TiSCH_K2_ENC_MIC128 = 14
