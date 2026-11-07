// desktape input helper for Windows (panel-live D5): a person's keyboard for the panel, as real input.
// The driver's keys stall for 2 s every few presses from the desktop scope (measured 2026-11-07); SendInput,
// what a keyboard does, does not. Compiled on the target with the .NET Framework's own csc.exe, once per version.
//
//   desktape-input serve <port> <token file>   in the desktop session (a one-off /it task): one connection on the
//                                              loopback, whose first line must be the token in the file (deleted
//                                              when read); then "text <base64 UTF-8>" and "keys <vk>,<vk>..." lines,
//                                              each answered "ok <events>"; ends with the connection, or after 20 s
//   desktape-input relay <port>                in the SSH session: standard input to that connection, answers to
//                                              standard output. .NET's console stream (and PowerShell's) hands over
//                                              only the first chunk of an SSH session's piped input and then waits
//                                              forever (measured 2026-11-08); ReadFile on the handle reads it all
//
// ASCII only.
using System;
using System.Collections.Generic;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;

static class DesktapeInput {
    [StructLayout(LayoutKind.Sequential)] struct KEYBDINPUT { public ushort wVk; public ushort wScan; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Sequential)] struct MOUSEINPUT { public int dx; public int dy; public uint mouseData; public uint dwFlags; public uint time; public IntPtr dwExtraInfo; }
    [StructLayout(LayoutKind.Explicit)] struct UNION { [FieldOffset(0)] public MOUSEINPUT mi; [FieldOffset(0)] public KEYBDINPUT ki; }
    [StructLayout(LayoutKind.Sequential)] struct INPUT { public uint type; public UNION u; }
    [DllImport("user32.dll", SetLastError = true)] static extern uint SendInput(uint n, INPUT[] inputs, int size);
    [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool ReadFile(IntPtr h, byte[] b, int n, out int got, IntPtr ov);

    static INPUT Key(ushort vk, ushort scan, uint flags) {
        INPUT i = new INPUT(); i.type = 1; i.u.ki.wVk = vk; i.u.ki.wScan = scan; i.u.ki.dwFlags = flags; return i;
    }
    static uint Ext(ushort vk) { return ((vk >= 0x21 && vk <= 0x2E) || vk == 0x5B) ? 1u : 0u; }   // arrows, Home..Delete, Win
    static uint Send(List<INPUT> l) { return SendInput((uint)l.Count, l.ToArray(), Marshal.SizeOf(typeof(INPUT))); }

    static string Handle(string line) {
        int sp = line.IndexOf(' ');
        string cmd = sp < 0 ? line : line.Substring(0, sp), arg = sp < 0 ? "" : line.Substring(sp + 1);
        List<INPUT> l = new List<INPUT>();
        if (cmd == "text") {
            foreach (char c in Encoding.UTF8.GetString(Convert.FromBase64String(arg))) {
                l.Add(Key(0, c, 4)); l.Add(Key(0, c, 4 | 2));          // KEYEVENTF_UNICODE: any layout, accents
            }
        } else if (cmd == "keys") {
            List<ushort> vks = new List<ushort>();
            foreach (string v in arg.Split(',')) vks.Add(ushort.Parse(v));
            foreach (ushort v in vks) l.Add(Key(v, 0, Ext(v)));
            for (int j = vks.Count - 1; j >= 0; j--) l.Add(Key(vks[j], 0, Ext(vks[j]) | 2));
        } else {
            return "err unknown " + cmd;
        }
        return "ok " + (l.Count == 0 ? 0 : Send(l));
    }

    static int Serve(int port, string tokenFile) {
        string token = File.ReadAllText(tokenFile).Trim();
        File.Delete(tokenFile);
        TcpListener listener = new TcpListener(IPAddress.Loopback, port);
        listener.Start();
        DateTime deadline = DateTime.Now.AddSeconds(20);
        while (!listener.Pending()) {
            if (DateTime.Now > deadline) { listener.Stop(); return 3; }
            Thread.Sleep(20);
        }
        TcpClient client = listener.AcceptTcpClient();
        listener.Stop();
        client.NoDelay = true;
        NetworkStream s = client.GetStream();
        StreamReader r = new StreamReader(s, Encoding.ASCII);
        StreamWriter w = new StreamWriter(s, Encoding.ASCII); w.AutoFlush = true;
        if (r.ReadLine() != token) { client.Close(); return 4; }
        w.WriteLine("ready");
        string line;
        while ((line = r.ReadLine()) != null) {
            try { w.WriteLine(Handle(line)); } catch (Exception e) { w.WriteLine("err " + e.Message.Replace('\n', ' ')); }
        }
        client.Close();
        return 0;
    }

    static int Relay(int port) {
        TcpClient c = null;
        for (int i = 0; i < 100 && c == null; i++) {
            try { c = new TcpClient("127.0.0.1", port); } catch (SocketException) { Thread.Sleep(200); }
        }
        if (c == null) { Console.Error.WriteLine("no helper on port " + port); return 2; }
        c.NoDelay = true;
        NetworkStream s = c.GetStream();
        StreamReader r = new StreamReader(s, Encoding.ASCII);
        StreamWriter w = new StreamWriter(s, Encoding.ASCII); w.AutoFlush = true;
        StreamWriter output = new StreamWriter(Console.OpenStandardOutput(), Encoding.ASCII); output.AutoFlush = true;
        IntPtr stdin = GetStdHandle(-10);
        byte[] buf = new byte[4096];
        StringBuilder pending = new StringBuilder();
        int got;
        while (ReadFile(stdin, buf, buf.Length, out got, IntPtr.Zero) && got > 0) {
            pending.Append(Encoding.ASCII.GetString(buf, 0, got));
            int nl;
            while ((nl = pending.ToString().IndexOf('\n')) >= 0) {
                string line = pending.ToString(0, nl).TrimEnd('\r');
                pending.Remove(0, nl + 1);
                w.WriteLine(line);
                string answer = r.ReadLine();
                if (answer == null) { c.Close(); return 0; }
                output.WriteLine(answer);
            }
        }
        c.Close();
        return 0;
    }

    static int Main(string[] a) {
        if (a.Length == 3 && a[0] == "serve") return Serve(int.Parse(a[1]), a[2]);
        if (a.Length == 2 && a[0] == "relay") return Relay(int.Parse(a[1]));
        Console.Error.WriteLine("usage: desktape-input serve <port> <token file> | relay <port>");
        return 1;
    }
}
