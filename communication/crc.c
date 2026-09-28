uint16_t AeplRfid_CalculateCrc16(const uint8_t * data,uint16_t length)
{
    '''
        #define AEPL_RFID_CRC_INITIAL_VALUE             (0xFFFFU)
        #define AEPL_RFID_CRC_POLYNOMIAL                (0x1021U)
        #define AEPL_RFID_CRC_MSB_MASK                  (0x8000U)
        #define AEPL_RFID_CRC_START_INDEX                0U
    '''

    uint16_t crc = AEPL_RFID_CRC_INITIAL_VALUE;
    uint16_t byte_index;
    uint8_t bit_index;
 
    if (data != NULL)
    {
        for (byte_index = AEPL_RFID_CRC_START_INDEX; byte_index < length; byte_index++)
        {
            crc ^= (uint16_t)((uint16_t)data[byte_index] << 8U);
 
            for (bit_index = 0U; bit_index < 8U; bit_index++)
            {
                if ((crc & AEPL_RFID_CRC_MSB_MASK) != 0U)
                {
                    crc = (uint16_t)((uint16_t)(crc << 1U) ^
                                     AEPL_RFID_CRC_POLYNOMIAL);
                }
                else
                {
                    crc = (uint16_t)(crc << 1U);
                }
            }
        }
    }
 
    return crc;
}