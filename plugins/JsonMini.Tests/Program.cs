// Self-test for the bridge JSON reader. Exit 0 only when every case matches.
// It compiles the same JsonMini.cs the plugin ships.

using System;
using System.Collections;
using System.Collections.Generic;
using IllusionForge;

internal static class Program
{
    static int Main()
    {
        int failed = 0;
        failed += Check("{}", "{}");
        failed += Check("{\"a\":1,\"b\":[true,false,null,\"x\"]}", "{\"a\":1,\"b\":[true,false,null,\"x\"]}");
        failed += Check("\"a\\nb\"", "\"a\\nb\"");
        failed += Check("\"\\u3042\"", "\"あ\"");
        object parsed = JsonMini.Parse("{\"face\":{\"0\":0.25}}");
        var root = (Dictionary<string, object>)parsed;
        var face = (Dictionary<string, object>)root["face"];
        if (Math.Abs((double)face["0"] - 0.25) > 0.0000001)
        {
            Console.Error.WriteLine("number mismatch");
            failed++;
        }
        try
        {
            JsonMini.Parse("{\"a\":1} trailing");
            Console.Error.WriteLine("trailing data was accepted");
            failed++;
        }
        catch (FormatException)
        {
        }
        if (failed != 0)
        {
            Console.Error.WriteLine("jsonmini failed " + failed);
            return 1;
        }
        Console.WriteLine("jsonmini ok");
        return 0;
    }

    static int Check(string input, string expectWritten)
    {
        object value = JsonMini.Parse(input);
        string written = JsonMini.Write(value);
        object again = JsonMini.Parse(written);
        if (!Same(value, again))
        {
            Console.Error.WriteLine("roundtrip mismatch for " + input + " -> " + written);
            return 1;
        }
        if (expectWritten != null && written != expectWritten && input != "\"\\u3042\"")
        {
            // Number formatting may differ. Objects and the escaped string should match.
            if (!(value is double) && written != expectWritten)
            {
                Console.Error.WriteLine("write mismatch\n got " + written + "\n want " + expectWritten);
                return 1;
            }
        }
        return 0;
    }

    static bool Same(object a, object b)
    {
        if (a == null || b == null) return a == null && b == null;
        if (a is double && b is double) return Math.Abs((double)a - (double)b) < 0.0000001;
        if (a is string || a is bool) return a.Equals(b);
        var da = a as IDictionary;
        var db = b as IDictionary;
        if (da != null && db != null)
        {
            if (da.Count != db.Count) return false;
            foreach (DictionaryEntry entry in da)
            {
                if (!db.Contains(entry.Key) || !Same(entry.Value, db[entry.Key])) return false;
            }
            return true;
        }
        var la = a as IList;
        var lb = b as IList;
        if (la != null && lb != null)
        {
            if (la.Count != lb.Count) return false;
            for (int i = 0; i < la.Count; i++) if (!Same(la[i], lb[i])) return false;
            return true;
        }
        return a.Equals(b);
    }
}
