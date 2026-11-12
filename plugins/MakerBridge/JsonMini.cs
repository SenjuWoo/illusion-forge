// Tiny JSON reader and writer for the maker bridge.
// BepInEx on these games does not ship Newtonsoft.Json, and a second copy of
// that library collides with other plugins. The debug log is the BepInEx log.
// This file has no Unity references so the self-test can compile it alone.

using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace IllusionForge
{
    public static class JsonMini
    {
        public static object Parse(string text)
        {
            if (text == null) throw new FormatException("json is null");
            var parser = new Parser(text);
            object value = parser.ReadValue();
            parser.Skip();
            if (!parser.End) throw new FormatException("trailing data after json");
            return value;
        }

        public static string Write(object value)
        {
            var builder = new StringBuilder();
            WriteInto(builder, value);
            return builder.ToString();
        }

        static void WriteInto(StringBuilder builder, object value)
        {
            if (value == null)
            {
                builder.Append("null");
                return;
            }
            if (value is bool flag)
            {
                builder.Append(flag ? "true" : "false");
                return;
            }
            if (value is string text)
            {
                WriteString(builder, text);
                return;
            }
            if (value is double || value is float || value is int || value is long)
            {
                double number = Convert.ToDouble(value, CultureInfo.InvariantCulture);
                builder.Append(number.ToString("R", CultureInfo.InvariantCulture));
                return;
            }
            var dict = value as IDictionary;
            if (dict != null)
            {
                builder.Append('{');
                bool first = true;
                foreach (DictionaryEntry entry in dict)
                {
                    if (!first) builder.Append(',');
                    first = false;
                    WriteString(builder, Convert.ToString(entry.Key, CultureInfo.InvariantCulture));
                    builder.Append(':');
                    WriteInto(builder, entry.Value);
                }
                builder.Append('}');
                return;
            }
            var list = value as IEnumerable;
            if (list != null)
            {
                builder.Append('[');
                bool first = true;
                foreach (object item in list)
                {
                    if (!first) builder.Append(',');
                    first = false;
                    WriteInto(builder, item);
                }
                builder.Append(']');
                return;
            }
            WriteString(builder, Convert.ToString(value, CultureInfo.InvariantCulture));
        }

        static void WriteString(StringBuilder builder, string text)
        {
            builder.Append('"');
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                switch (c)
                {
                    case '"': builder.Append("\\\""); break;
                    case '\\': builder.Append("\\\\"); break;
                    case '\b': builder.Append("\\b"); break;
                    case '\f': builder.Append("\\f"); break;
                    case '\n': builder.Append("\\n"); break;
                    case '\r': builder.Append("\\r"); break;
                    case '\t': builder.Append("\\t"); break;
                    default:
                        if (c < 32) builder.Append("\\u").Append(((int)c).ToString("x4"));
                        else builder.Append(c);
                        break;
                }
            }
            builder.Append('"');
        }

        sealed class Parser
        {
            readonly string _text;
            int _index;

            public Parser(string text)
            {
                _text = text;
            }

            public bool End { get { return _index >= _text.Length; } }

            public void Skip()
            {
                while (_index < _text.Length && char.IsWhiteSpace(_text[_index])) _index++;
            }

            public object ReadValue()
            {
                Skip();
                if (End) throw new FormatException("unexpected end");
                char c = _text[_index];
                if (c == '{') return ReadObject();
                if (c == '[') return ReadArray();
                if (c == '"') return ReadString();
                if (c == 't' || c == 'f') return ReadBool();
                if (c == 'n') return ReadNull();
                return ReadNumber();
            }

            Dictionary<string, object> ReadObject()
            {
                Expect('{');
                var map = new Dictionary<string, object>();
                Skip();
                if (Peek('}')) { _index++; return map; }
                while (true)
                {
                    Skip();
                    string key = ReadString();
                    Skip();
                    Expect(':');
                    map[key] = ReadValue();
                    Skip();
                    if (Peek('}')) { _index++; return map; }
                    Expect(',');
                }
            }

            List<object> ReadArray()
            {
                Expect('[');
                var list = new List<object>();
                Skip();
                if (Peek(']')) { _index++; return list; }
                while (true)
                {
                    list.Add(ReadValue());
                    Skip();
                    if (Peek(']')) { _index++; return list; }
                    Expect(',');
                }
            }

            string ReadString()
            {
                Expect('"');
                var builder = new StringBuilder();
                while (!End)
                {
                    char c = _text[_index++];
                    if (c == '"') return builder.ToString();
                    if (c != '\\') { builder.Append(c); continue; }
                    if (End) throw new FormatException("bad escape");
                    char esc = _text[_index++];
                    switch (esc)
                    {
                        case '"':
                        case '\\':
                        case '/': builder.Append(esc); break;
                        case 'b': builder.Append('\b'); break;
                        case 'f': builder.Append('\f'); break;
                        case 'n': builder.Append('\n'); break;
                        case 'r': builder.Append('\r'); break;
                        case 't': builder.Append('\t'); break;
                        case 'u':
                            if (_index + 4 > _text.Length) throw new FormatException("bad unicode escape");
                            int code = int.Parse(_text.Substring(_index, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
                            builder.Append((char)code);
                            _index += 4;
                            break;
                        default: throw new FormatException("bad escape");
                    }
                }
                throw new FormatException("unterminated string");
            }

            object ReadBool()
            {
                if (Match("true")) return true;
                if (Match("false")) return false;
                throw new FormatException("expected boolean");
            }

            object ReadNull()
            {
                if (!Match("null")) throw new FormatException("expected null");
                return null;
            }

            double ReadNumber()
            {
                int start = _index;
                if (Peek('-')) _index++;
                while (!End && char.IsDigit(_text[_index])) _index++;
                if (Peek('.'))
                {
                    _index++;
                    while (!End && char.IsDigit(_text[_index])) _index++;
                }
                if (!End && (_text[_index] == 'e' || _text[_index] == 'E'))
                {
                    _index++;
                    if (Peek('+') || Peek('-')) _index++;
                    while (!End && char.IsDigit(_text[_index])) _index++;
                }
                string slice = _text.Substring(start, _index - start);
                double number;
                if (!double.TryParse(slice, NumberStyles.Float, CultureInfo.InvariantCulture, out number))
                    throw new FormatException("bad number");
                return number;
            }

            bool Peek(char c) { return !End && _text[_index] == c; }

            void Expect(char c)
            {
                Skip();
                if (End || _text[_index] != c) throw new FormatException("expected " + c);
                _index++;
            }

            bool Match(string word)
            {
                if (_index + word.Length > _text.Length) return false;
                if (string.CompareOrdinal(_text, _index, word, 0, word.Length) != 0) return false;
                _index += word.Length;
                return true;
            }
        }
    }
}
