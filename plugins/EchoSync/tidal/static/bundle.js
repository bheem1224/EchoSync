//#region node_modules/svelte/src/internal/disclose-version.js
typeof window < "u" && ((window.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5");
//#endregion
//#region node_modules/svelte/src/internal/flags/index.js
var e = !1, t = !1;
function n() {
	t = !0;
}
//#endregion
//#region node_modules/svelte/src/internal/flags/legacy.js
n();
//#endregion
//#region node_modules/svelte/src/constants.js
var r = {}, i = Symbol("uninitialized"), a = "http://www.w3.org/1999/xhtml", o = Array.isArray, s = Array.prototype.indexOf, c = Array.prototype.includes, l = Array.from, u = Object.keys, d = Object.defineProperty, f = Object.getOwnPropertyDescriptor, p = Object.getOwnPropertyDescriptors, m = Object.prototype, h = Array.prototype, g = Object.getPrototypeOf, _ = Object.isExtensible, v = () => {};
function y(e) {
	return e();
}
function b(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function x() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
var S = 1024, C = 2048, w = 4096, ee = 8192, te = 16384, ne = 32768, re = 1 << 25, ie = 65536, ae = 1 << 19, oe = 1 << 20, se = 1 << 25, ce = 65536, le = 1 << 21, ue = 1 << 22, de = 1 << 23, fe = Symbol("$state"), pe = Symbol("legacy props"), me = Symbol(""), he = Symbol("attributes"), ge = Symbol("class"), _e = Symbol("style"), ve = Symbol("text"), ye = Symbol("form reset"), be = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), xe = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml");
function Se(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
//#endregion
//#region node_modules/svelte/src/internal/client/errors.js
function Ce() {
	throw Error("https://svelte.dev/e/async_derived_orphan");
}
function we(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function Te(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ee() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function De(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Oe() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function ke() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Ae(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function je() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Me() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Ne() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Pe() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
function Fe() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function Ie(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function Le() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/hydration.js
var T = !1;
function Re(e) {
	T = e;
}
var E;
function D(e) {
	if (e === null) throw Ie(), r;
	return E = e;
}
function ze() {
	return D(/* @__PURE__ */ un(E));
}
function O(e) {
	if (T) {
		if (/* @__PURE__ */ un(E) !== null) throw Ie(), r;
		E = e;
	}
}
function Be(e = 1) {
	if (T) {
		for (var t = e, n = E; t--;) n = /* @__PURE__ */ un(n);
		E = n;
	}
}
function Ve(e = !0) {
	for (var t = 0, n = E;;) {
		if (n.nodeType === 8) {
			var r = n.data;
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ un(n);
		e && n.remove(), n = i;
	}
}
function He(e) {
	if (!e || e.nodeType !== 8) throw Ie(), r;
	return e.data;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/equality.js
function Ue(e) {
	return e === this.v;
}
function We(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Ge(e) {
	return !We(e, this.v);
}
//#endregion
//#region node_modules/svelte/src/internal/client/context.js
var k = null;
function Ke(e) {
	k = e;
}
function qe(e, n = !1, r) {
	k = {
		p: k,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: t && !n ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Je(e) {
	var t = k, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) Tn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, k = t.p, e ?? {};
}
function Ye() {
	return !t || k !== null && k.l === null;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/task.js
var Xe = [];
function Ze() {
	var e = Xe;
	Xe = [], b(e);
}
function Qe(e) {
	if (Xe.length === 0 && !pt) {
		var t = Xe;
		queueMicrotask(() => {
			t === Xe && Ze();
		});
	}
	Xe.push(e);
}
function $e() {
	for (; Xe.length > 0;) Ze();
}
function et(e) {
	var t = W;
	if (t === null) return V.f |= de, e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	tt(e, t);
}
function tt(e, t) {
	for (; t !== null;) {
		if (t.f & 128) {
			if (!(t.f & 32768)) throw e;
			try {
				t.b.error(e);
				return;
			} catch (t) {
				e = t;
			}
		}
		t = t.parent;
	}
	throw e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/status.js
var nt = ~(C | w | S);
function A(e, t) {
	e.f = e.f & nt | t;
}
function rt(e) {
	e.f & 512 || e.deps === null ? A(e, S) : A(e, w);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/utils.js
function it(e) {
	if (e !== null) for (let t of e) !(t.f & 2) || !(t.f & 65536) || (t.f ^= ce, it(t.deps));
}
function at(e, t, n) {
	e.f & 2048 ? t.add(e) : e.f & 4096 && n.add(e), it(e.deps), A(e, S);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/store.js
var ot = !1, st = !1;
function ct(e) {
	var t = st;
	try {
		return st = !1, [e(), st];
	} finally {
		st = t;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/batch.js
var lt = null, ut = null, j = null, dt = null, M = null, ft = null, pt = !1, mt = !1, ht = null, gt = null, _t = 0, vt = 1, yt = class t {
	id = vt++;
	#e = !1;
	linked = !0;
	#t = null;
	#n = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	unblocked = /* @__PURE__ */ new Set();
	#r = /* @__PURE__ */ new Set();
	#i = /* @__PURE__ */ new Set();
	#a = /* @__PURE__ */ new Set();
	#o = 0;
	#s = /* @__PURE__ */ new Map();
	#c = null;
	#l = [];
	#u = [];
	#d = /* @__PURE__ */ new Set();
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Map();
	#m = /* @__PURE__ */ new Set();
	is_fork = !1;
	#h = !1;
	#g() {
		if (this.is_fork) return !0;
		for (let n of this.#s.keys()) {
			for (var e = n, t = !1; e.parent !== null;) {
				if (this.#p.has(e)) {
					t = !0;
					break;
				}
				e = e.parent;
			}
			if (!t) return !0;
		}
		return !1;
	}
	skip_effect(e) {
		this.#p.has(e) || this.#p.set(e, {
			d: [],
			m: []
		}), this.#m.delete(e);
	}
	unskip_effect(e, t = (e) => this.schedule(e)) {
		var n = this.#p.get(e);
		if (n) {
			this.#p.delete(e);
			for (var r of n.d) A(r, C), t(r);
			for (r of n.m) A(r, w), t(r);
		}
		this.#m.add(e);
	}
	#_() {
		if (this.#e = !0, _t++ > 1e3 && (this.#w(), xt()), !this.#g()) {
			for (let e of this.#d) this.#f.delete(e), A(e, C), this.schedule(e);
			for (let e of this.#f) A(e, w), this.schedule(e);
		}
		let n = this.#l;
		this.#l = [], this.apply();
		var r = ht = [], i = [], a = gt = [];
		for (let e of n) try {
			this.#v(e, r, i);
		} catch (t) {
			throw Ot(e), t;
		}
		if (j = null, a.length > 0) {
			var o = t.ensure();
			for (let e of a) o.schedule(e);
		}
		if (ht = null, gt = null, this.#g()) {
			this.#x(i), this.#x(r);
			for (let [e, t] of this.#p) Dt(e, t);
			a.length > 0 && j.#_();
			return;
		}
		let s = this.#y();
		if (s) {
			s.#b(this);
			return;
		}
		this.#d.clear(), this.#f.clear();
		for (let e of this.#r) e(this);
		this.#r.clear(), dt = this, Ct(i), Ct(r), dt = null, this.#c?.resolve();
		var c = j;
		if (this.linked && this.#o === 0 && this.#w(), e && !this.linked && (this.#S(), j = c), this.#l.length > 0) {
			c === null && (c = this, this.#C());
			let e = c;
			e.#l.push(...this.#l.filter((t) => !e.#l.includes(t)));
		}
		c !== null && c.#_();
	}
	#v(t, n, r) {
		t.f ^= S;
		for (var i = t.first; i !== null;) {
			var a = i.f, o = (a & 96) != 0;
			if (!(o && a & 1024 || a & 8192 || this.#p.has(i)) && i.fn !== null) {
				o ? i.f ^= S : a & 4 ? n.push(i) : e && a & 16777224 ? r.push(i) : nr(i) && (a & 16 && this.#f.add(i), sr(i));
				var s = i.first;
				if (s !== null) {
					i = s;
					continue;
				}
			}
			for (; i !== null;) {
				var c = i.next;
				if (c !== null) {
					i = c;
					break;
				}
				i = i.parent;
			}
		}
	}
	#y() {
		for (var e = this.#t; e !== null;) {
			if (!e.is_fork) {
				for (let [t, [, n]] of this.current) if (e.current.has(t) && !n) return e;
			}
			e = e.#t;
		}
		return null;
	}
	#b(e) {
		for (let [t, n] of e.current) !this.previous.has(t) && e.previous.has(t) && this.previous.set(t, e.previous.get(t)), this.current.set(t, n);
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && n.promise.then(e.resolve);
		}
		let t = (e) => {
			var n = e.reactions;
			if (n !== null) for (let e of n) {
				var r = e.f;
				if (r & 2) t(e);
				else {
					var i = e;
					r & 4194320 && !this.async_deriveds.has(i) && (this.#f.delete(i), A(i, C), this.schedule(i));
				}
			}
		};
		for (let e of this.current.keys()) t(e);
		this.oncommit(() => e.discard()), e.#w(), j = this, this.#_();
	}
	#x(e) {
		for (var t = 0; t < e.length; t += 1) at(e[t], this.#d, this.#f);
	}
	capture(e, t, n = !1) {
		e.v !== i && !this.previous.has(e) && this.previous.set(e, e.v), e.f & 8388608 || (this.current.set(e, [t, n]), M?.set(e, t)), this.is_fork || (e.v = t);
	}
	activate() {
		j = this;
	}
	deactivate() {
		j = null, M = null;
	}
	flush() {
		try {
			mt = !0, j = this, this.#_();
		} finally {
			_t = 0, ft = null, ht = null, gt = null, mt = !1, j = null, M = null, qt.clear();
		}
	}
	discard() {
		for (let e of this.#i) e(this);
		this.#i.clear(), this.#a.clear(), this.#w();
	}
	register_created_effect(e) {
		this.#u.push(e);
	}
	#S() {
		this.#w();
		for (let l = lt; l !== null; l = l.#n) {
			var e = l.id < this.id, t = [];
			for (let [r, [i, a]] of this.current) {
				if (l.current.has(r)) {
					var n = l.current.get(r)[0];
					if (e && i !== n) l.current.set(r, [i, a]);
					else continue;
				}
				t.push(r);
			}
			if (e) for (let [e, t] of this.async_deriveds) {
				let n = l.async_deriveds.get(e);
				n && t.promise.then(n.resolve);
			}
			if (l.#e) {
				var r = [...l.current.keys()].filter((e) => !this.current.has(e));
				if (r.length === 0) e && l.discard();
				else if (t.length > 0) {
					if (e) for (let e of this.#m) l.unskip_effect(e, (e) => {
						e.f & 4194320 ? l.schedule(e) : l.#x([e]);
					});
					l.activate();
					var i = /* @__PURE__ */ new Set(), a = /* @__PURE__ */ new Map();
					for (var o of t) wt(o, r, i, a);
					a = /* @__PURE__ */ new Map();
					var s = [...l.current.keys()].filter((e) => this.current.has(e) ? this.current.get(e)[0] !== e.v : !0);
					if (s.length > 0) for (let e of this.#u) !(e.f & 155648) && Tt(e, s, a) && (e.f & 4194320 ? (A(e, C), l.schedule(e)) : l.#d.add(e));
					if (l.#l.length > 0) {
						l.apply();
						for (var c of l.#l) l.#v(c, [], []);
						l.#l = [];
					}
					l.deactivate();
				}
			}
		}
	}
	increment(e, t) {
		if (this.#o += 1, e) {
			let e = this.#s.get(t) ?? 0;
			this.#s.set(t, e + 1);
		}
	}
	decrement(e, t) {
		if (--this.#o, e) {
			let e = this.#s.get(t) ?? 0;
			e === 1 ? this.#s.delete(t) : this.#s.set(t, e - 1);
		}
		this.#h || (this.#h = !0, Qe(() => {
			this.#h = !1, this.linked && this.flush();
		}));
	}
	transfer_effects(e, t) {
		for (let t of e) this.#d.add(t);
		for (let e of t) this.#f.add(e);
		e.clear(), t.clear();
	}
	oncommit(e) {
		this.#r.add(e);
	}
	ondiscard(e) {
		this.#i.add(e);
	}
	on_fork_commit(e) {
		this.#a.add(e);
	}
	run_fork_commit_callbacks() {
		for (let e of this.#a) e(this);
		this.#a.clear();
	}
	settled() {
		return (this.#c ??= x()).promise;
	}
	static ensure() {
		if (j === null) {
			let e = j = new t();
			e.#C(), !mt && !pt && Qe(() => {
				e.#e || e.flush();
			});
		}
		return j;
	}
	apply() {
		if (!e || !this.is_fork && this.#t === null && this.#n === null) {
			M = null;
			return;
		}
		M = /* @__PURE__ */ new Map();
		for (let [e, [t]] of this.current) M.set(e, t);
		for (let e = lt; e !== null; e = e.#n) if (!(e === this || e.is_fork)) {
			var t = !1;
			if (e.id < this.id) {
				for (let [n, [, r]] of e.current) if (!r && this.current.has(n)) {
					t = !0;
					break;
				}
			}
			if (!t) for (let [t, n] of e.previous) M.has(t) || M.set(t, n);
		}
	}
	schedule(t) {
		if (ft = t, t.b?.is_pending && t.f & 16777228 && !(t.f & 32768)) {
			t.b.defer_effect(t);
			return;
		}
		for (var n = t; n.parent !== null;) {
			n = n.parent;
			var r = n.f;
			if (ht !== null && n === W && (e || (V === null || !(V.f & 2)) && !ot)) return;
			if (r & 96) {
				if (!(r & 1024)) return;
				n.f ^= S;
			}
		}
		this.#l.push(n);
	}
	#C() {
		ut === null ? lt = ut = this : (ut.#n = this, this.#t = ut), ut = this;
	}
	#w() {
		var e = this.#t, t = this.#n;
		e === null ? lt = t : e.#n = t, t === null ? ut = e : t.#t = e, this.linked = !1;
	}
};
function bt(e) {
	var t = pt;
	pt = !0;
	try {
		var n;
		for (e && (j !== null && !j.is_fork && j.flush(), n = e());;) {
			if ($e(), j === null) return n;
			j.flush();
		}
	} finally {
		pt = t;
	}
}
function xt() {
	try {
		Oe();
	} catch (e) {
		tt(e, ft);
	}
}
var St = null;
function Ct(e) {
	var t = e.length;
	if (t !== 0) {
		for (var n = 0; n < t;) {
			var r = e[n++];
			if (!(r.f & 24576) && nr(r) && (St = /* @__PURE__ */ new Set(), sr(r), r.deps === null && r.first === null && r.nodes === null && r.teardown === null && r.ac === null && Rn(r), St?.size > 0)) {
				qt.clear();
				for (let e of St) {
					if (e.f & 24576) continue;
					let t = [e], n = e.parent;
					for (; n !== null;) St.has(n) && (St.delete(n), t.push(n)), n = n.parent;
					for (let e = t.length - 1; e >= 0; e--) {
						let n = t[e];
						n.f & 24576 || sr(n);
					}
				}
				St.clear();
			}
		}
		St = null;
	}
}
function wt(e, t, n, r) {
	if (!n.has(e) && (n.add(e), e.reactions !== null)) for (let i of e.reactions) {
		let e = i.f;
		e & 2 ? wt(i, t, n, r) : e & 4194320 && !(e & 2048) && Tt(i, t, r) && (A(i, C), Et(i));
	}
}
function Tt(e, t, n) {
	let r = n.get(e);
	if (r !== void 0) return r;
	if (e.deps !== null) for (let r of e.deps) {
		if (c.call(t, r)) return !0;
		if (r.f & 2 && Tt(r, t, n)) return n.set(r, !0), !0;
	}
	return n.set(e, !1), !1;
}
function Et(e) {
	j.schedule(e);
}
function Dt(e, t) {
	if (!(e.f & 32 && e.f & 1024)) {
		e.f & 2048 ? t.d.push(e) : e.f & 4096 && t.m.push(e), A(e, S);
		for (var n = e.first; n !== null;) Dt(n, t), n = n.next;
	}
}
function Ot(e) {
	A(e, S);
	for (var t = e.first; t !== null;) Ot(t), t = t.next;
}
//#endregion
//#region node_modules/svelte/src/reactivity/create-subscriber.js
function kt(e) {
	let t = 0, n = Yt(0), r;
	return () => {
		Sn() && (Y(n), jn(() => (t === 0 && (r = X(() => e(() => en(n)))), t += 1, () => {
			Qe(() => {
				--t, t === 0 && (r?.(), r = void 0, en(n));
			});
		})));
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var At = ie | ae;
function jt(e, t, n, r) {
	new Mt(e, t, n, r);
}
var Mt = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = T ? E : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = 0;
	#d = !1;
	#f = /* @__PURE__ */ new Set();
	#p = /* @__PURE__ */ new Set();
	#m = null;
	#h = kt(() => (this.#m = Yt(this.#l), () => {
		this.#m = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = Nn(() => {
			if (T) {
				let e = this.#t;
				ze();
				let t = e.data === "[!";
				if (e.data.startsWith("[?")) {
					let t = JSON.parse(e.data.slice(2));
					this.#_(t);
				} else t ? this.#v() : this.#g();
			} else this.#y();
		}, At), T && (this.#e = E);
	}
	#g() {
		try {
			this.#a = z(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#_(e) {
		let t = this.#n.failed;
		t && (this.#s = z(() => {
			t(this.#e, () => e, () => () => {});
		}));
	}
	#v() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = z(() => e(this.#e)), Qe(() => {
			var e = this.#c = document.createDocumentFragment(), t = F();
			e.append(t), this.#a = this.#x(() => z(() => this.#r(t))), this.#u === 0 && (this.#e.before(e), this.#c = null, zn(this.#o, () => {
				this.#o = null;
			}), this.#b(j));
		}));
	}
	#y() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#u = 0, this.#l = 0, this.#a = z(() => {
				this.#r(this.#e);
			}), this.#u > 0) {
				var e = this.#c = document.createDocumentFragment();
				Un(this.#a, e);
				let t = this.#n.pending;
				this.#o = z(() => t(this.#e));
			} else this.#b(j);
		} catch (e) {
			this.error(e);
		}
	}
	#b(e) {
		this.is_pending = !1, e.transfer_effects(this.#f, this.#p);
	}
	defer_effect(e) {
		at(e, this.#f, this.#p);
	}
	is_rendered() {
		return !this.is_pending && (!this.parent || this.parent.is_rendered());
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = W, n = V, r = k;
		Jn(this.#i), U(this.#i), Ke(this.#i.ctx);
		try {
			return yt.ensure(), e();
		} catch (e) {
			return et(e), null;
		} finally {
			Jn(t), U(n), Ke(r);
		}
	}
	#S(e, t) {
		if (!this.has_pending_snippet()) {
			this.parent && this.parent.#S(e, t);
			return;
		}
		this.#u += e, this.#u === 0 && (this.#b(t), this.#o && zn(this.#o, () => {
			this.#o = null;
		}), this.#c &&= (this.#e.before(this.#c), null));
	}
	update_pending_count(e, t) {
		this.#S(e, t), this.#l += e, !(!this.#m || this.#d) && (this.#d = !0, Qe(() => {
			this.#d = !1, this.#m && Qt(this.#m, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#h(), Y(this.#m);
	}
	error(e) {
		if (!this.#n.onerror && !this.#n.failed) throw e;
		j?.is_fork ? (this.#a && j.skip_effect(this.#a), this.#o && j.skip_effect(this.#o), this.#s && j.skip_effect(this.#s), j.on_fork_commit(() => {
			this.#C(e);
		})) : this.#C(e);
	}
	#C(e) {
		this.#a &&= (B(this.#a), null), this.#o &&= (B(this.#o), null), this.#s &&= (B(this.#s), null), T && (D(this.#t), Be(), D(Ve()));
		var t = this.#n.onerror;
		let n = this.#n.failed;
		var r = !1, i = !1;
		let a = () => {
			if (r) {
				Le();
				return;
			}
			r = !0, i && Pe(), this.#s !== null && zn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#y();
			});
		}, o = (e) => {
			try {
				i = !0, t?.(e, a), i = !1;
			} catch (e) {
				tt(e, this.#i && this.#i.parent);
			}
			n && (this.#s = this.#x(() => {
				try {
					return z(() => {
						var t = W;
						t.b = this, t.f |= 128, n(this.#e, () => e, () => a);
					});
				} catch (e) {
					return tt(e, this.#i.parent), null;
				}
			}));
		};
		Qe(() => {
			var t;
			try {
				t = this.transform_error(e);
			} catch (e) {
				tt(e, this.#i && this.#i.parent);
				return;
			}
			typeof t == "object" && t && typeof t.then == "function" ? t.then(o, (e) => tt(e, this.#i && this.#i.parent)) : o(t);
		});
	}
};
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/async.js
function Nt(e, t, n, r) {
	let i = Ye() ? Lt : Bt;
	var a = e.filter((e) => !e.settled);
	if (n.length === 0 && a.length === 0) {
		r(t.map(i));
		return;
	}
	var o = W, s = Pt(), c = a.length === 1 ? a[0].promise : a.length > 1 ? Promise.all(a.map((e) => e.promise)) : null;
	function l(e) {
		if (!(o.f & 16384)) {
			s();
			try {
				r(e);
			} catch (e) {
				tt(e, o);
			}
			Ft();
		}
	}
	var u = It();
	if (n.length === 0) {
		c.then(() => l(t.map(i))).finally(u);
		return;
	}
	function d() {
		Promise.all(n.map((e) => /* @__PURE__ */ zt(e))).then((e) => l([...t.map(i), ...e])).catch((e) => tt(e, o)).finally(u);
	}
	c ? c.then(() => {
		s(), d(), Ft();
	}) : d();
}
function Pt() {
	var e = W, t = V, n = k, r = j;
	return function(i = !0) {
		Jn(e), U(t), Ke(n), i && !(e.f & 16384) && (r?.activate(), r?.apply());
	};
}
function Ft(e = !0) {
	Jn(null), U(null), Ke(null), e && j?.deactivate();
}
function It() {
	var e = W, t = e.b, n = j, r = t.is_rendered();
	return t.update_pending_count(1, n), n.increment(r, e), () => {
		t.update_pending_count(-1, n), n.decrement(r, e);
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Lt(e) {
	var t = 2 | C;
	return W !== null && (W.f |= ae), {
		ctx: k,
		deps: null,
		effects: null,
		equals: Ue,
		f: t,
		fn: e,
		reactions: null,
		rv: 0,
		v: i,
		wv: 0,
		parent: W,
		ac: null
	};
}
var Rt = Symbol("obsolete");
/* @__NO_SIDE_EFFECTS__ */
function zt(e, t, n) {
	let r = W;
	r === null && Ce();
	var a = void 0, o = Yt(i), s = !V, c = /* @__PURE__ */ new Set();
	return An(() => {
		var t = W, n = x();
		a = n.promise;
		try {
			Promise.resolve(e()).then(n.resolve, (e) => {
				e !== be && n.reject(e);
			}).finally(Ft);
		} catch (e) {
			n.reject(e), Ft();
		}
		var i = j;
		if (s) {
			if (t.f & 32768) var l = It();
			if (r.b.is_rendered()) i.async_deriveds.get(t)?.reject(Rt);
			else for (let e of c.values()) e.reject(Rt);
			c.add(n), i.async_deriveds.set(t, n);
		}
		let u = (e, t = void 0) => {
			l?.(), c.delete(n), t !== Rt && (i.activate(), t ? (o.f |= de, Qt(o, t)) : (o.f & 8388608 && (o.f ^= de), Qt(o, e)), i.deactivate());
		};
		n.promise.then(u, (e) => u(null, e || "unknown"));
	}), Cn(() => {
		for (let e of c) e.reject(Rt);
	}), new Promise((e) => {
		function t(n) {
			function r() {
				n === a ? e(o) : t(a);
			}
			n.then(r, r);
		}
		t(a);
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Bt(e) {
	let t = /* @__PURE__ */ Lt(e);
	return t.equals = Ge, t;
}
function Vt(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) B(t[n]);
	}
}
function Ht(e) {
	var t, n = W, r = e.parent;
	if (!Kn && r !== null && e.v !== i && r.f & 24576) return Fe(), e.v;
	Jn(r);
	try {
		e.f &= ~ce, Vt(e), t = ir(e);
	} finally {
		Jn(n);
	}
	return t;
}
function Ut(e) {
	var t = Ht(e);
	if (!e.equals(t) && (e.wv = tr(), (!j?.is_fork || e.deps === null) && (j === null ? e.v = t : (j.capture(e, t, !0), dt?.capture(e, t, !0)), e.deps === null))) {
		A(e, S);
		return;
	}
	Kn || (M === null ? rt(e) : (Sn() || j?.is_fork) && M.set(e, t));
}
function Wt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.ac) && (t.teardown?.(), t.ac?.abort(be), t.fn !== null && (t.teardown = v), t.ac = null, or(t, 0), Fn(t));
}
function Gt(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && sr(t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/sources.js
var Kt = /* @__PURE__ */ new Set(), qt = /* @__PURE__ */ new Map(), Jt = !1;
function Yt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Ue,
		rv: 0,
		wv: 0
	};
}
/* @__NO_SIDE_EFFECTS__ */
function Xt(e, t) {
	let n = Yt(e, t);
	return Yn(n), n;
}
/* @__NO_SIDE_EFFECTS__ */
function N(e, n = !1, r = !0) {
	let i = Yt(e);
	return n || (i.equals = Ge), t && r && k !== null && k.l !== null && (k.l.s ??= []).push(i), i;
}
function Zt(e, t) {
	return P(e, X(() => Y(e))), t;
}
function P(e, t, n = !1) {
	return V !== null && (!H || V.f & 131072) && Ye() && V.f & 4325394 && (G === null || !c.call(G, e)) && Ne(), Qt(e, n ? nn(t) : t, gt);
}
function Qt(e, t, n = null) {
	if (!e.equals(t)) {
		qt.set(e, Kn ? t : e.v);
		var r = yt.ensure();
		if (r.capture(e, t), e.f & 2) {
			let t = e;
			e.f & 2048 && Ht(t), M === null && rt(t);
		}
		e.wv = tr(), tn(e, C, n), Ye() && W !== null && W.f & 1024 && !(W.f & 96) && (J === null ? Xn([e]) : J.push(e)), !r.is_fork && Kt.size > 0 && !Jt && $t();
	}
	return t;
}
function $t() {
	Jt = !1;
	for (let e of Kt) {
		e.f & 1024 && A(e, w);
		let t;
		try {
			t = nr(e);
		} catch {
			t = !0;
		}
		t && sr(e);
	}
	Kt.clear();
}
function en(e) {
	P(e, e.v + 1);
}
function tn(e, t, n) {
	var r = e.reactions;
	if (r !== null) for (var i = Ye(), a = r.length, o = 0; o < a; o++) {
		var s = r[o], c = s.f;
		if (!(!i && s === W)) {
			var l = (c & C) === 0;
			if (l && A(s, t), c & 131072) Kt.add(s);
			else if (c & 2) {
				var u = s;
				M?.delete(u), c & 65536 || (c & 512 && (W === null || !(W.f & 2097152)) && (s.f |= ce), tn(u, w, n));
			} else if (l) {
				var d = s;
				c & 16 && St !== null && St.add(d), n === null ? Et(d) : n.push(d);
			}
		}
	}
}
function nn(e) {
	if (typeof e != "object" || !e || fe in e) return e;
	let t = g(e);
	if (t !== m && t !== h) return e;
	var n = /* @__PURE__ */ new Map(), r = o(e), a = /* @__PURE__ */ Xt(0), s = null, c = $n, l = (e) => {
		if ($n === c) return e();
		var t = V, n = $n;
		U(null), er(c);
		var r = e();
		return U(t), er(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ Xt(e.length, s)), new Proxy(e, {
		defineProperty(e, t, r) {
			(!("value" in r) || r.configurable === !1 || r.enumerable === !1 || r.writable === !1) && je();
			var i = n.get(t);
			return i === void 0 ? l(() => {
				var e = /* @__PURE__ */ Xt(r.value, s);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = l(() => /* @__PURE__ */ Xt(i, s));
					n.set(t, e), en(a);
				}
			} else P(r, i), en(a);
			return !0;
		},
		get(t, r, a) {
			if (r === fe) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || f(t, r)?.writable) && (o = l(() => /* @__PURE__ */ Xt(nn(c ? t[r] : i), s)), n.set(r, o)), o !== void 0) {
				var u = Y(o);
				return u === i ? void 0 : u;
			}
			return Reflect.get(t, r, a);
		},
		getOwnPropertyDescriptor(e, t) {
			var r = Reflect.getOwnPropertyDescriptor(e, t);
			if (r && "value" in r) {
				var a = n.get(t);
				a && (r.value = Y(a));
			} else if (r === void 0) {
				var o = n.get(t), s = o?.v;
				if (o !== void 0 && s !== i) return {
					enumerable: !0,
					configurable: !0,
					value: s,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === fe) return !0;
			var r = n.get(t), a = r !== void 0 && r.v !== i || Reflect.has(e, t);
			return (r !== void 0 || W !== null && (!a || f(e, t)?.writable)) && (r === void 0 && (r = l(() => /* @__PURE__ */ Xt(a ? nn(e[t]) : i, s)), n.set(t, r)), Y(r) === i) ? !1 : a;
		},
		set(e, t, o, c) {
			var u = n.get(t), d = t in e;
			if (r && t === "length") for (var p = o; p < u.v; p += 1) {
				var m = n.get(p + "");
				m === void 0 ? p in e && (m = l(() => /* @__PURE__ */ Xt(i, s)), n.set(p + "", m)) : P(m, i);
			}
			if (u === void 0) (!d || f(e, t)?.writable) && (u = l(() => /* @__PURE__ */ Xt(void 0, s)), P(u, nn(o)), n.set(t, u));
			else {
				d = u.v !== i;
				var h = l(() => nn(o));
				P(u, h);
			}
			var g = Reflect.getOwnPropertyDescriptor(e, t);
			if (g?.set && g.set.call(c, o), !d) {
				if (r && typeof t == "string") {
					var _ = n.get("length"), v = Number(t);
					Number.isInteger(v) && v >= _.v && P(_, v + 1);
				}
				en(a);
			}
			return !0;
		},
		ownKeys(e) {
			Y(a);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== i;
			});
			for (var [r, o] of n) o.v !== i && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Me();
		}
	});
}
var rn, an, on, sn;
function cn() {
	if (rn === void 0) {
		rn = window, an = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		on = f(t, "firstChild").get, sn = f(t, "nextSibling").get, _(e) && (e[ge] = void 0, e[he] = null, e[_e] = void 0, e.__e = void 0), _(n) && (n[ve] = void 0);
	}
}
function F(e = "") {
	return document.createTextNode(e);
}
/* @__NO_SIDE_EFFECTS__ */
function ln(e) {
	return on.call(e);
}
/* @__NO_SIDE_EFFECTS__ */
function un(e) {
	return sn.call(e);
}
function I(e, t) {
	if (!T) return /* @__PURE__ */ ln(e);
	var n = /* @__PURE__ */ ln(E);
	if (n === null) n = E.appendChild(F());
	else if (t && n.nodeType !== 3) {
		var r = F();
		return n?.before(r), D(r), r;
	}
	return t && hn(n), D(n), n;
}
function dn(e, t = !1) {
	if (!T) {
		var n = /* @__PURE__ */ ln(e);
		return n instanceof Comment && n.data === "" ? /* @__PURE__ */ un(n) : n;
	}
	if (t) {
		if (E?.nodeType !== 3) {
			var r = F();
			return E?.before(r), D(r), r;
		}
		hn(E);
	}
	return E;
}
function L(e, t = 1, n = !1) {
	let r = T ? E : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ un(r);
	if (!T) return r;
	if (n) {
		if (r?.nodeType !== 3) {
			var a = F();
			return r === null ? i?.after(a) : r.before(a), D(a), a;
		}
		hn(r);
	}
	return D(r), r;
}
function fn(e) {
	e.textContent = "";
}
function pn() {
	return !e || St !== null ? !1 : (W.f & ne) !== 0;
}
function mn(e, t, n) {
	let r = n ? { is: n } : void 0;
	return document.createElementNS(t ?? "http://www.w3.org/1999/xhtml", e, r);
}
function hn(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && t.nodeType === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/misc.js
var gn = !1;
function _n() {
	gn || (gn = !0, document.addEventListener("reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[ye]?.();
		});
	}, { capture: !0 }));
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function vn(e) {
	var t = V, n = W;
	U(null), Jn(null);
	try {
		return e();
	} finally {
		U(t), Jn(n);
	}
}
function yn(e, t, n, r = n) {
	e.addEventListener(t, () => vn(n));
	let i = e[ye];
	i ? e[ye] = () => {
		i(), r(!0);
	} : e[ye] = () => r(!0), _n();
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/effects.js
function bn(e) {
	W === null && (V === null && De(e), Ee()), Kn && Te(e);
}
function xn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function R(e, t) {
	var n = W;
	n !== null && n.f & 8192 && (e |= ee);
	var r = {
		ctx: k,
		deps: null,
		nodes: null,
		f: e | C | 512,
		first: null,
		fn: t,
		last: null,
		next: null,
		parent: n,
		b: n && n.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null
	};
	j?.register_created_effect(r);
	var i = r;
	if (e & 4) ht === null ? yt.ensure().schedule(r) : ht.push(r);
	else if (t !== null) {
		try {
			sr(r);
		} catch (e) {
			throw B(r), e;
		}
		i.deps === null && i.teardown === null && i.nodes === null && i.first === i.last && !(i.f & 524288) && (i = i.first, e & 16 && e & 65536 && i !== null && (i.f |= ie));
	}
	if (i !== null && (i.parent = n, n !== null && xn(i, n), V !== null && V.f & 2 && !(e & 64))) {
		var a = V;
		(a.effects ??= []).push(i);
	}
	return r;
}
function Sn() {
	return V !== null && !H;
}
function Cn(e) {
	let t = R(8, null);
	return A(t, S), t.teardown = e, t;
}
function wn(e) {
	bn("$effect");
	var t = W.f;
	if (!V && t & 32 && !(t & 32768)) {
		var n = k;
		(n.e ??= []).push(e);
	} else return Tn(e);
}
function Tn(e) {
	return R(4 | oe, e);
}
function En(e) {
	return bn("$effect.pre"), R(8 | oe, e);
}
function Dn(e) {
	yt.ensure();
	let t = R(64 | ae, e);
	return () => {
		B(t);
	};
}
function On(e) {
	yt.ensure();
	let t = R(64 | ae, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? zn(t, () => {
			B(t), n(void 0);
		}) : (B(t), n(void 0));
	});
}
function kn(e) {
	return R(4, e);
}
function An(e) {
	return R(ue | ae, e);
}
function jn(e, t = 0) {
	return R(8 | t, e);
}
function Mn(e, t = [], n = [], r = []) {
	Nt(r, t, n, (t) => {
		R(8, () => e(...t.map(Y)));
	});
}
function Nn(e, t = 0) {
	return R(16 | t, e);
}
function z(e) {
	return R(32 | ae, e);
}
function Pn(e) {
	var t = e.teardown;
	if (t !== null) {
		let e = Kn, n = V;
		qn(!0), U(null);
		try {
			t.call(null);
		} finally {
			qn(e), U(n);
		}
	}
}
function Fn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		let e = n.ac;
		e !== null && vn(() => {
			e.abort(be);
		});
		var r = n.next;
		n.f & 64 ? n.parent = null : B(n, t), n = r;
	}
}
function In(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || B(t), t = n;
	}
}
function B(e, t = !0) {
	var n = !1;
	(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (Ln(e.nodes.start, e.nodes.end), n = !0), A(e, re), Fn(e, t && !n), or(e, 0);
	var r = e.nodes && e.nodes.t;
	if (r !== null) for (let e of r) e.stop();
	Pn(e), e.f ^= re, e.f |= te;
	var i = e.parent;
	i !== null && i.first !== null && Rn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.fn = e.nodes = e.ac = e.b = null;
}
function Ln(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ un(e);
		e.remove(), e = n;
	}
}
function Rn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function zn(e, t, n = !0) {
	var r = [];
	Bn(e, r, !0);
	var i = () => {
		n && B(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = () => --a || i();
		for (var s of r) s.out(o);
	} else i();
}
function Bn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= ee;
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) (e.is_global || n) && t.push(e);
		for (var i = e.first; i !== null;) {
			var a = i.next;
			if (!(i.f & 64)) {
				var o = (i.f & 65536) != 0 || (i.f & 32) != 0 && (e.f & 16) != 0;
				Bn(i, t, o ? n : !1);
			}
			i = a;
		}
	}
}
function Vn(e) {
	Hn(e, !0);
}
function Hn(e, t) {
	if (e.f & 8192) {
		e.f ^= ee, e.f & 1024 || (A(e, C), yt.ensure().schedule(e));
		for (var n = e.first; n !== null;) {
			var r = n.next, i = (n.f & 65536) != 0 || (n.f & 32) != 0;
			Hn(n, i ? t : !1), n = r;
		}
		var a = e.nodes && e.nodes.t;
		if (a !== null) for (let e of a) (e.is_global || t) && e.in();
	}
}
function Un(e, t) {
	if (e.nodes) for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
		var i = n === r ? null : /* @__PURE__ */ un(n);
		t.append(n), n = i;
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/legacy.js
var Wn = null, Gn = !1, Kn = !1;
function qn(e) {
	Kn = e;
}
var V = null, H = !1;
function U(e) {
	V = e;
}
var W = null;
function Jn(e) {
	W = e;
}
var G = null;
function Yn(t) {
	V !== null && (!e || V.f & 2) && (G === null ? G = [t] : G.push(t));
}
var K = null, q = 0, J = null;
function Xn(e) {
	J = e;
}
var Zn = 1, Qn = 0, $n = Qn;
function er(e) {
	$n = e;
}
function tr() {
	return ++Zn;
}
function nr(e) {
	var t = e.f;
	if (t & 2048) return !0;
	if (t & 2 && (e.f &= ~ce), t & 4096) {
		for (var n = e.deps, r = n.length, i = 0; i < r; i++) {
			var a = n[i];
			if (nr(a) && Ut(a), a.wv > e.wv) return !0;
		}
		t & 512 && M === null && A(e, S);
	}
	return !1;
}
function rr(t, n, r = !0) {
	var i = t.reactions;
	if (i !== null && !(!e && G !== null && c.call(G, t))) for (var a = 0; a < i.length; a++) {
		var o = i[a];
		o.f & 2 ? rr(o, n, !1) : n === o && (r ? A(o, C) : o.f & 1024 && A(o, w), Et(o));
	}
}
function ir(e) {
	var t = K, n = q, r = J, i = V, a = G, o = k, s = H, c = $n, l = e.f;
	K = null, q = 0, J = null, V = l & 96 ? null : e, G = null, Ke(e.ctx), H = !1, $n = ++Qn, e.ac !== null && (vn(() => {
		e.ac.abort(be);
	}), e.ac = null);
	try {
		e.f |= le;
		var u = e.fn, d = u();
		e.f |= ne;
		var f = e.deps, p = j?.is_fork;
		if (K !== null) {
			var m;
			if (p || or(e, q), f !== null && q > 0) for (f.length = q + K.length, m = 0; m < K.length; m++) f[q + m] = K[m];
			else e.deps = f = K;
			if (Sn() && e.f & 512) for (m = q; m < f.length; m++) (f[m].reactions ??= []).push(e);
		} else !p && f !== null && q < f.length && (or(e, q), f.length = q);
		if (Ye() && J !== null && !H && f !== null && !(e.f & 6146)) for (m = 0; m < J.length; m++) rr(J[m], e);
		if (i !== null && i !== e) {
			if (Qn++, i.deps !== null) for (let e = 0; e < n; e += 1) i.deps[e].rv = Qn;
			if (t !== null) for (let e of t) e.rv = Qn;
			J !== null && (r === null ? r = J : r.push(...J));
		}
		return e.f & 8388608 && (e.f ^= de), d;
	} catch (e) {
		return et(e);
	} finally {
		e.f ^= le, K = t, q = n, J = r, V = i, G = a, Ke(o), H = s, $n = c;
	}
}
function ar(e, t) {
	let n = t.reactions;
	if (n !== null) {
		var r = s.call(n, e);
		if (r !== -1) {
			var a = n.length - 1;
			a === 0 ? n = t.reactions = null : (n[r] = n[a], n.pop());
		}
	}
	if (n === null && t.f & 2 && (K === null || !c.call(K, t))) {
		var o = t;
		o.f & 512 && (o.f ^= 512, o.f &= ~ce), o.v !== i && rt(o), Wt(o), or(o, 0);
	}
}
function or(e, t) {
	var n = e.deps;
	if (n !== null) for (var r = t; r < n.length; r++) ar(e, n[r]);
}
function sr(e) {
	var t = e.f;
	if (!(t & 16384)) {
		A(e, S);
		var n = W, r = Gn;
		W = e, Gn = !0;
		try {
			t & 16777232 ? In(e) : Fn(e), Pn(e);
			var i = ir(e);
			e.teardown = typeof i == "function" ? i : null, e.wv = Zn;
		} finally {
			Gn = r, W = n;
		}
	}
}
async function cr() {
	if (e) return new Promise((e) => {
		requestAnimationFrame(() => e()), setTimeout(() => e());
	});
	await Promise.resolve(), bt();
}
function Y(e) {
	var t = (e.f & 2) != 0;
	if (Wn?.add(e), V !== null && !H && !(W !== null && W.f & 16384) && (G === null || !c.call(G, e))) {
		var n = V.deps;
		if (V.f & 2097152) e.rv < Qn && (e.rv = Qn, K === null && n !== null && n[q] === e ? q++ : K === null ? K = [e] : K.push(e));
		else {
			(V.deps ??= []).push(e);
			var r = e.reactions;
			r === null ? e.reactions = [V] : c.call(r, V) || r.push(V);
		}
	}
	if (Kn && qt.has(e)) return qt.get(e);
	if (t) {
		var i = e;
		if (Kn) {
			var a = i.v;
			return (!(i.f & 1024) && i.reactions !== null || ur(i)) && (a = Ht(i)), qt.set(i, a), a;
		}
		var o = (i.f & 512) == 0 && !H && V !== null && (Gn || (V.f & 512) != 0), s = (i.f & ne) === 0;
		nr(i) && (o && (i.f |= 512), Ut(i)), o && !s && (Gt(i), lr(i));
	}
	if (M?.has(e)) return M.get(e);
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function lr(e) {
	if (e.f |= 512, e.deps !== null) for (let t of e.deps) (t.reactions ??= []).push(e), t.f & 2 && !(t.f & 512) && (Gt(t), lr(t));
}
function ur(e) {
	if (e.v === i) return !0;
	if (e.deps === null) return !1;
	for (let t of e.deps) if (qt.has(t) || t.f & 2 && ur(t)) return !0;
	return !1;
}
function X(e) {
	var t = H;
	try {
		return H = !0, e();
	} finally {
		H = t;
	}
}
function dr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (fe in e) fr(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && fe in n && fr(n);
		}
	}
}
function fr(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			fr(e[n], t);
		} catch {}
		let n = g(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = p(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/events.js
var pr = Symbol("events"), mr = /* @__PURE__ */ new Set(), hr = /* @__PURE__ */ new Set();
function gr(e, t, n, r = {}) {
	function i(e) {
		if (r.capture || vr.call(t, e), !e.cancelBubble) return vn(() => n?.call(this, e));
	}
	return e.startsWith("pointer") || e.startsWith("touch") || e === "wheel" ? Qe(() => {
		t.addEventListener(e, i, r);
	}) : t.addEventListener(e, i, r), i;
}
function Z(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = gr(e, t, n, a);
	(t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && Cn(() => {
		t.removeEventListener(e, o, a);
	});
}
var _r = null;
function vr(e) {
	var t = this, n = t.ownerDocument, r = e.type, i = e.composedPath?.() || [], a = i[0] || e.target;
	_r = e;
	var o = 0, s = _r === e && e[pr];
	if (s) {
		var c = i.indexOf(s);
		if (c !== -1 && (t === document || t === window)) {
			e[pr] = t;
			return;
		}
		var l = i.indexOf(t);
		if (l === -1) return;
		c <= l && (o = c);
	}
	if (a = i[o] || e.target, a !== t) {
		d(e, "currentTarget", {
			configurable: !0,
			get() {
				return a || n;
			}
		});
		var u = V, f = W;
		U(null), Jn(null);
		try {
			for (var p, m = []; a !== null;) {
				var h = a.assignedSlot || a.parentNode || a.host || null;
				try {
					var g = a[pr]?.[r];
					g != null && (!a.disabled || e.target === a) && g.call(a, e);
				} catch (e) {
					p ? m.push(e) : p = e;
				}
				if (e.cancelBubble || h === t || h === null) break;
				a = h;
			}
			if (p) {
				for (let e of m) queueMicrotask(() => {
					throw e;
				});
				throw p;
			}
		} finally {
			e[pr] = t, delete e.currentTarget, U(u), Jn(f);
		}
	}
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/reconciler.js
var yr = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function br(e) {
	return yr?.createHTML(e) ?? e;
}
function xr(e) {
	var t = mn("template");
	return t.innerHTML = br(e.replaceAll("<!>", "<!---->")), t.content;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/template.js
function Sr(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/* @__NO_SIDE_EFFECTS__ */
function Q(e, t) {
	var n = (t & 1) != 0, r = (t & 2) != 0, i, a = !e.startsWith("<!>");
	return () => {
		if (T) return Sr(E, null), E;
		i === void 0 && (i = xr(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ ln(i)));
		var t = r || an ? document.importNode(i, !0) : i.cloneNode(!0);
		if (n) {
			var o = /* @__PURE__ */ ln(t), s = t.lastChild;
			Sr(o, s);
		} else Sr(t, t);
		return t;
	};
}
function $(e, t) {
	if (T) {
		var n = W;
		(!(n.f & 32768) || n.nodes.end === null) && (n.nodes.end = E), ze();
		return;
	}
	e !== null && e.before(t);
}
[.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var Cr = ["touchstart", "touchmove"];
function wr(e) {
	return Cr.includes(e);
}
function Tr(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[ve] ??= e.nodeValue) && (e[ve] = n, e.nodeValue = `${n}`);
}
function Er(e, t) {
	return kr(e, t);
}
function Dr(e, t) {
	cn(), t.intro = t.intro ?? !1;
	let n = t.target, i = T, a = E;
	try {
		for (var o = /* @__PURE__ */ ln(n); o && (o.nodeType !== 8 || o.data !== "[");) o = /* @__PURE__ */ un(o);
		if (!o) throw r;
		Re(!0), D(o);
		let i = kr(e, {
			...t,
			anchor: o
		});
		return Re(!1), i;
	} catch (i) {
		if (i instanceof Error && i.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw i;
		return i !== r && console.warn("Failed to hydrate: ", i), t.recover === !1 && ke(), cn(), fn(n), Re(!1), Er(e, t);
	} finally {
		Re(i), D(a);
	}
}
var Or = /* @__PURE__ */ new Map();
function kr(e, { target: t, anchor: n, props: i = {}, events: a, context: o, intro: s = !0, transformError: c }) {
	cn();
	var u = void 0, d = On(() => {
		var s = n ?? t.appendChild(F());
		jt(s, { pending: () => {} }, (t) => {
			qe({});
			var n = k;
			if (o && (n.c = o), a && (i.$$events = a), T && Sr(t, null), u = e(t, i) || {}, T && (W.nodes.end = E, E === null || E.nodeType !== 8 || E.data !== "]")) throw Ie(), r;
			Je();
		}, c);
		var d = /* @__PURE__ */ new Set(), f = (e) => {
			for (var n = 0; n < e.length; n++) {
				var r = e[n];
				if (!d.has(r)) {
					d.add(r);
					var i = wr(r);
					for (let e of [t, document]) {
						var a = Or.get(e);
						a === void 0 && (a = /* @__PURE__ */ new Map(), Or.set(e, a));
						var o = a.get(r);
						o === void 0 ? (e.addEventListener(r, vr, { passive: i }), a.set(r, 1)) : a.set(r, o + 1);
					}
				}
			}
		};
		return f(l(mr)), hr.add(f), () => {
			for (var e of d) for (let n of [t, document]) {
				var r = Or.get(n), i = r.get(e);
				--i == 0 ? (n.removeEventListener(e, vr), r.delete(e), r.size === 0 && Or.delete(n)) : r.set(e, i);
			}
			hr.delete(f), s !== n && s.parentNode?.removeChild(s);
		};
	});
	return Ar.set(u, d), u;
}
var Ar = /* @__PURE__ */ new WeakMap();
function jr(e, t) {
	let n = Ar.get(e);
	return n ? (Ar.delete(e), n(t)) : Promise.resolve();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Mr = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t;
	}
	#a = (e) => {
		if (this.#e.has(e)) {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) Vn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (this.#t.set(t, r.effect), this.#n.delete(t), r.fragment.lastChild.remove(), this.anchor.before(r.fragment), n = r.effect);
			}
			for (let [t, n] of this.#e) {
				if (this.#e.delete(t), t === e) break;
				let r = this.#n.get(n);
				r && (B(r.effect), this.#n.delete(n));
			}
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = document.createDocumentFragment();
						Un(r, t), t.append(F()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else B(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), zn(r, i, !1)) : i();
			}
		}
	};
	#o = (e) => {
		this.#e.delete(e);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (B(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = j, r = pn();
		if (t && !this.#t.has(e) && !this.#n.has(e)) if (r) {
			var i = document.createDocumentFragment(), a = F();
			i.append(a), this.#n.set(e, {
				effect: z(() => t(a)),
				fragment: i
			});
		} else this.#t.set(e, z(() => t(this.anchor)));
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#a), n.ondiscard(this.#o);
		} else T && (this.anchor = E), this.#a(n);
	}
};
function Nr(e) {
	k === null && Se("onMount"), t && k.l !== null ? Pr(k).m.push(e) : wn(() => {
		let t = X(e);
		if (typeof t == "function") return t;
	});
}
function Pr(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/if.js
function Fr(e, t, n = !1) {
	var r;
	T && (r = E, ze());
	var i = new Mr(e), a = n ? ie : 0;
	function o(e, t) {
		if (T) {
			var n = He(r);
			if (e !== parseInt(n.substring(1))) {
				var a = Ve();
				D(a), i.anchor = a, Re(!1), i.ensure(e, t), Re(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	Nn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, o(n, t);
		}), e || o(-1, null);
	}, a);
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/blocks/each.js
function Ir(e, t) {
	return t;
}
function Lr(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		zn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Rr(e, l(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null;
		if (c) {
			var u = n, d = u.parentNode;
			fn(d), d.append(u), e.items.clear();
		}
		Rr(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Rr(e, t, n = !0) {
	var r;
	if (e.pending.size > 0) {
		r = /* @__PURE__ */ new Set();
		for (let t of e.pending.values()) for (let n of t) r.add(e.items.get(n).e);
	}
	for (var i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= se, Un(a, document.createDocumentFragment())) : B(t[i], n);
	}
}
var zr;
function Br(e, t, n, r, i, a = null) {
	var s = e, c = /* @__PURE__ */ new Map();
	if (t & 4) {
		var u = e;
		s = T ? D(/* @__PURE__ */ ln(u)) : u.appendChild(F());
	}
	T && ze();
	var d = null, f = /* @__PURE__ */ Bt(() => {
		var e = n();
		return o(e) ? e : e == null ? [] : l(e);
	}), p, m = /* @__PURE__ */ new Map(), h = !0;
	function g(e) {
		v.effect.f & 16384 || (v.pending.delete(e), v.fallback = d, Hr(v, p, s, t, r), d !== null && (p.length === 0 ? d.f & 33554432 ? (d.f ^= se, Wr(d, null, s)) : Vn(d) : zn(d, () => {
			d = null;
		})));
	}
	function _(e) {
		v.pending.delete(e);
	}
	var v = {
		effect: Nn(() => {
			p = Y(f);
			var e = p.length;
			let o = !1;
			T && He(s) === "[!" != (e === 0) && (s = Ve(), D(s), Re(!1), o = !0);
			for (var l = /* @__PURE__ */ new Set(), u = j, v = pn(), y = 0; y < e; y += 1) {
				T && E.nodeType === 8 && E.data === "]" && (s = E, o = !0, Re(!1));
				var b = p[y], x = r(b, y), S = h ? null : c.get(x);
				S ? (S.v && Qt(S.v, b), S.i && Qt(S.i, y), v && u.unskip_effect(S.e)) : (S = Ur(c, h ? s : zr ??= F(), b, x, y, i, t, n), h || (S.e.f |= se), c.set(x, S)), l.add(x);
			}
			if (e === 0 && a && !d && (h ? d = z(() => a(s)) : (d = z(() => a(zr ??= F())), d.f |= se)), e > l.size && we("", "", ""), T && e > 0 && D(Ve()), !h) if (m.set(u, l), v) {
				for (let [e, t] of c) l.has(e) || u.skip_effect(t.e);
				u.oncommit(g), u.ondiscard(_);
			} else g(u);
			o && Re(!0), Y(f);
		}),
		flags: t,
		items: c,
		pending: m,
		outrogroups: null,
		fallback: d
	};
	h = !1, T && (s = E);
}
function Vr(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function Hr(e, t, n, r, i) {
	var a = (r & 8) != 0, o = t.length, s = e.items, c = Vr(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (Vn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) if (_.f ^= se, _ === c) Wr(_, null, n);
		else {
			var y = d ? d.next : c;
			_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), Gr(e, d, _), Gr(e, _, y), Wr(_, y, n), d = _, p = [], m = [], c = Vr(d.next);
			continue;
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) Wr(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					Gr(e, S.prev, C.next), Gr(e, d, S), Gr(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), Wr(_, c, n), Gr(e, _.prev, _.next), Gr(e, _, d === null ? e.effect.first : d.next), Gr(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = Vr(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = Vr(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Rr(e, l(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = Vr(c.next);
		var ee = w.length;
		if (ee > 0) {
			var te = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Lr(e, w, te);
		}
	}
	a && Qe(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function Ur(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? Yt(n) : /* @__PURE__ */ N(n, !1, !1) : null, l = o & 2 ? Yt(i) : null;
	return {
		v: c,
		i: l,
		e: z(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function Wr(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ un(r);
		if (a.before(r), r === i) return;
		r = o;
	}
}
function Gr(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/css.js
function Kr(e, t) {
	kn(() => {
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = mn("style");
			e.id = t.hash, e.textContent = t.code, r.appendChild(e);
		}
	});
}
//#endregion
//#region node_modules/svelte/src/internal/shared/attributes.js
var qr = [..." 	\n\r\f\xA0\v﻿"];
function Jr(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || qr.includes(r[o - 1])) && (s === r.length || qr.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/class.js
function Yr(e, t, n, r, i, a) {
	var o = e[ge];
	if (T || o !== n || o === void 0) {
		var s = Jr(n, r, a);
		(!T || s !== e.getAttribute("class")) && (s == null ? e.removeAttribute("class") : t ? e.className = s : e.setAttribute("class", s)), e[ge] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && e.classList.toggle(c, l);
	}
	return a;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/attributes.js
var Xr = Symbol("is custom element"), Zr = Symbol("is html"), Qr = xe ? "link" : "LINK";
function $r(e) {
	if (T) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, e.hasAttribute("value")) {
					var n = e.value;
					ei(e, "value", null), e.value = n;
				}
				if (e.hasAttribute("checked")) {
					var r = e.checked;
					ei(e, "checked", null), e.checked = r;
				}
			}
		};
		e[ye] = n, Qe(n), _n();
	}
}
function ei(e, t, n, r) {
	var i = ti(e);
	T && (i[t] = e.getAttribute(t), t === "src" || t === "srcset" || t === "href" && e.nodeName === Qr) || i[t] !== (i[t] = n) && (t === "loading" && (e[me] = n), n == null ? e.removeAttribute(t) : typeof n != "string" && ri(e).includes(t) ? e[t] = n : e.setAttribute(t, n));
}
function ti(e) {
	return e[he] ??= {
		[Xr]: e.nodeName.includes("-"),
		[Zr]: e.namespaceURI === a
	};
}
var ni = /* @__PURE__ */ new Map();
function ri(e) {
	var t = e.getAttribute("is") || e.nodeName, n = ni.get(t);
	if (n) return n;
	ni.set(t, n = []);
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = p(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.push(o);
		i = g(i);
	}
	return n;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function ii(t, n, r = n) {
	var i = /* @__PURE__ */ new WeakSet();
	yn(t, "input", async (e) => {
		var a = e ? t.defaultValue : t.value;
		if (a = ai(t) ? oi(a) : a, r(a), j !== null && i.add(j), await cr(), a !== (a = n())) {
			var o = t.selectionStart, s = t.selectionEnd, c = t.value.length;
			if (t.value = a ?? "", s !== null) {
				var l = t.value.length;
				o === s && s === c && l > c ? (t.selectionStart = l, t.selectionEnd = l) : (t.selectionStart = o, t.selectionEnd = Math.min(s, l));
			}
		}
	}), (T && t.defaultValue !== t.value || X(n) == null && t.value) && (r(ai(t) ? oi(t.value) : t.value), j !== null && i.add(j)), jn(() => {
		var r = n();
		if (t === document.activeElement) {
			var a = e ? dt : j;
			if (i.has(a)) return;
		}
		ai(t) && r === oi(t.value) || t.type === "date" && !r && !t.value || r !== t.value && (t.value = r ?? "");
	});
}
function ai(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function oi(e) {
	return e === "" ? null : +e;
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function si(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function ci(e = !1) {
	let t = k, n = t.l.u;
	if (!n) return;
	let r = () => dr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ Lt(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && En(() => {
		li(t, r), b(n.b);
	}), wn(() => {
		let e = X(() => n.m.map(y));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && wn(() => {
		li(t, r), b(n.a);
	});
}
function li(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
//#endregion
//#region node_modules/svelte/src/internal/client/dom/legacy/misc.js
function ui(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of o(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
//#endregion
//#region node_modules/svelte/src/internal/client/reactivity/props.js
function di(e, n, r, i) {
	var a = !t || (r & 2) != 0, o = (r & 8) != 0, s = (r & 16) != 0, c = i, l = !0, u = void 0, d = () => s && a ? (u ??= /* @__PURE__ */ Lt(i), Y(u)) : (l && (l = !1, c = s ? X(i) : i), c);
	let p;
	if (o) {
		var m = fe in e || pe in e;
		p = f(e, n)?.set ?? (m && n in e ? (t) => e[n] = t : void 0);
	}
	var h, g = !1;
	o ? [h, g] = ct(() => e[n]) : h = e[n], h === void 0 && i !== void 0 && (h = d(), p && (a && Ae(n), p(h)));
	var _ = a ? () => {
		var t = e[n];
		return t === void 0 ? d() : (l = !0, t);
	} : () => {
		var t = e[n];
		return t !== void 0 && (c = void 0), t === void 0 ? c : t;
	};
	if (a && !(r & 4)) return _;
	if (p) {
		var v = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!a || !t || v || g) && p(t ? _() : e), e) : _();
		});
	}
	var y = !1, b = (r & 1 ? Lt : Bt)(() => (y = !1, _()));
	o && Y(b);
	var x = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(b) : a && o ? nn(e) : e;
			return P(b, n), y = !0, c !== void 0 && (c = n), e;
		}
		return Kn && y || x.f & 16384 ? b.v : Y(b);
	});
}
//#endregion
//#region node_modules/svelte/src/legacy/legacy-client.js
function fi(e) {
	return new pi(e);
}
var pi = class {
	#e;
	#t;
	constructor(t) {
		var n = /* @__PURE__ */ new Map(), r = (e, t) => {
			var r = /* @__PURE__ */ N(t, !1, !1);
			return n.set(e, r), r;
		};
		let i = new Proxy({
			...t.props || {},
			$$events: {}
		}, {
			get(e, t) {
				return Y(n.get(t) ?? r(t, Reflect.get(e, t)));
			},
			has(e, t) {
				return t === pe ? !0 : (Y(n.get(t) ?? r(t, Reflect.get(e, t))), Reflect.has(e, t));
			},
			set(e, t, i) {
				return P(n.get(t) ?? r(t, i), i), Reflect.set(e, t, i);
			}
		});
		this.#t = (t.hydrate ? Dr : Er)(t.component, {
			target: t.target,
			anchor: t.anchor,
			props: i,
			context: t.context,
			intro: t.intro ?? !1,
			recover: t.recover,
			transformError: t.transformError
		}), !e && (!t?.props?.$$host || t.sync === !1) && bt(), this.#e = i.$$events;
		for (let e of Object.keys(this.#t)) e === "$set" || e === "$destroy" || e === "$on" || d(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(i, e);
		}, this.#t.$destroy = () => {
			jr(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, mi;
typeof HTMLElement == "function" && (mi = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = mn("slot");
					e !== "default" && (n.name = e), $(t, n);
				};
			}
			let t = {}, n = gi(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = hi(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = fi({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = Dn(() => {
				jn(() => {
					this.$$r = !0;
					for (let e of u(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = hi(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = hi(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return u(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function hi(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function gi(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function _i(e, t, n, r, i, a) {
	let o = class extends mi {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return u(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return u(t).forEach((e) => {
		d(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = hi(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (f(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		d(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
//#endregion
//#region TidalCard.svelte
var vi = /* @__PURE__ */ Q("<div class=\"loading-state svelte-11pw7by\">Loading...</div>"), yi = /* @__PURE__ */ Q("<div class=\"redirect-copy-group svelte-11pw7by\"><input type=\"text\" class=\"input-field readonly text-wrap svelte-11pw7by\" readonly=\"\"/> <button class=\"btn-primary copy-btn svelte-11pw7by\">Copy</button></div> <p class=\"helper-text svelte-11pw7by\">This auto-generated URI must be registered in your Tidal Developer Applications.</p>", 1), bi = /* @__PURE__ */ Q("<button class=\"btn-ghost svelte-11pw7by\">+ Add Account</button>"), xi = /* @__PURE__ */ Q("<span class=\"status-badge success svelte-11pw7by\">✓ Authenticated</span>"), Si = /* @__PURE__ */ Q("<span class=\"status-badge warning svelte-11pw7by\">⚠ Not Authenticated</span>"), Ci = /* @__PURE__ */ Q("<span class=\"status-badge active svelte-11pw7by\">● Active</span>"), wi = /* @__PURE__ */ Q("<div class=\"account-item svelte-11pw7by\"><div class=\"account-info svelte-11pw7by\"><div class=\"account-name svelte-11pw7by\"> </div> <div class=\"account-badges svelte-11pw7by\"><!> <!></div></div> <div class=\"account-actions svelte-11pw7by\"><button class=\"link-btn svelte-11pw7by\">⚙️ Edit</button> <button class=\"link-btn svelte-11pw7by\"> </button> <button> </button> <button class=\"btn-danger svelte-11pw7by\">✕</button></div></div>"), Ti = /* @__PURE__ */ Q("<div class=\"empty-accounts svelte-11pw7by\">No accounts added yet. Click \"Add Account\" to get started.</div>"), Ei = /* @__PURE__ */ Q("<div class=\"settings-section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"section-title svelte-11pw7by\">Global Redirect URI (Immutable)</h3> <button class=\"btn-ghost svelte-11pw7by\"> </button></div> <!></div> <div class=\"settings-section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"section-title svelte-11pw7by\"> </h3> <!></div> <div class=\"accounts-list svelte-11pw7by\"></div></div>", 1), Di = /* @__PURE__ */ Q("<div class=\"modal-overlay svelte-11pw7by\"><div class=\"modal-content svelte-11pw7by\"><div class=\"modal-header svelte-11pw7by\"><h3 class=\"modal-title svelte-11pw7by\"> </h3> <button class=\"close-btn svelte-11pw7by\">✕</button></div> <div class=\"modal-body svelte-11pw7by\"><label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Account Name</span> <input type=\"text\" placeholder=\"My Tidal Account\" class=\"input-field svelte-11pw7by\"/></label> <label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Client ID</span> <input type=\"text\" placeholder=\"Enter Tidal Client ID\" class=\"input-field svelte-11pw7by\"/></label> <label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Client Secret</span> <div class=\"password-wrapper svelte-11pw7by\"><input placeholder=\"Enter Tidal Client Secret\" class=\"input-field svelte-11pw7by\"/> <button type=\"button\" class=\"toggle-visibility svelte-11pw7by\"> </button></div></label></div> <div class=\"modal-footer svelte-11pw7by\"><button class=\"btn-ghost svelte-11pw7by\">Cancel</button> <button class=\"btn-primary svelte-11pw7by\"> </button></div></div></div>"), Oi = /* @__PURE__ */ Q("<section class=\"plugin-card svelte-11pw7by\"><div class=\"card-header svelte-11pw7by\"><div class=\"header-left svelte-11pw7by\"><h2 class=\"card-title svelte-11pw7by\">Tidal</h2> <span class=\"type-badge svelte-11pw7by\">Streaming Service</span></div></div> <!></section> <!>", 1), ki = {
	hash: "svelte-11pw7by",
	code: ".plugin-card.svelte-11pw7by {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-11pw7by {display:flex;align-items:center;gap:12px;}.card-title.svelte-11pw7by {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-11pw7by {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-11pw7by {padding:24px;text-align:center;color:var(--text-muted);}.settings-section.svelte-11pw7by {margin-bottom:24px;}.section-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-11pw7by {margin:0;font-size:16px;font-weight:600;color:var(--text-primary);}.input-field.svelte-11pw7by {width:100%;padding:10px 14px;background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:8px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-11pw7by:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-11pw7by {opacity:0.6;cursor:not-allowed;}.helper-text.svelte-11pw7by {font-size:11px;color:var(--text-muted);margin-top:4px;}.redirect-copy-group.svelte-11pw7by {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-11pw7by .input-field:where(.svelte-11pw7by) {flex:1;font-family:monospace;overflow:hidden;text-overflow:ellipsis;}.text-wrap.svelte-11pw7by {word-break:break-all;white-space:normal;height:auto;min-height:40px;}.copy-btn.svelte-11pw7by {padding:0 16px;height:auto;white-space:nowrap;}.accounts-list.svelte-11pw7by {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);border-radius:8px;}.account-info.svelte-11pw7by {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-11pw7by {font-weight:600;font-size:14px;}.account-badges.svelte-11pw7by {display:flex;gap:8px;}.status-badge.svelte-11pw7by {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11pw7by {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-11pw7by {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11pw7by {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-11pw7by {display:flex;gap:12px;align-items:center;}.link-btn.svelte-11pw7by {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-11pw7by:hover {text-decoration:underline;}.btn-ghost.svelte-11pw7by {padding:8px 16px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:var(--text-primary);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-11pw7by:hover {background:rgba(255,255,255,0.1);}.btn-primary.svelte-11pw7by {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11pw7by:hover {opacity:0.9;}.btn-danger.svelte-11pw7by {background:rgba(239, 68, 68, 0.15);color:var(--color-danger);border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.modal-overlay.svelte-11pw7by {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-11pw7by {background:#0f1216;border:1px solid var(--border-subtle);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-11pw7by {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-11pw7by {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-11pw7by {background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;}.modal-body.svelte-11pw7by {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-11pw7by {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.form-field.svelte-11pw7by {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11pw7by {font-size:13px;color:var(--text-muted);}.password-wrapper.svelte-11pw7by {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11pw7by {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary);}.empty-accounts.svelte-11pw7by {text-align:center;padding:16px;color:var(--text-muted);font-size:13px;background:rgba(255,255,255,0.02);border-radius:8px;border:1px dashed rgba(255,255,255,0.1);}"
};
function Ai(e, t) {
	qe(t, !1), Kr(e, ki);
	let n = di(t, "apiBase", 12, ""), r = /* @__PURE__ */ N([]), i = /* @__PURE__ */ N(""), a = /* @__PURE__ */ N(!1), o = /* @__PURE__ */ N(!0), s = /* @__PURE__ */ N(!1), c = /* @__PURE__ */ N("add"), l = /* @__PURE__ */ N({
		id: null,
		account_name: "",
		client_id: "",
		client_secret: ""
	}), u = /* @__PURE__ */ N(!1), d = /* @__PURE__ */ N(!1);
	Nr(async () => {
		await f(), P(a, !!Y(i)), P(o, !1);
	});
	async function f() {
		try {
			let e = await (await fetch(`${n()}`)).json();
			e && (P(r, e.accounts || []), P(i, e.redirect_uri || ""), P(a, !!Y(i)));
		} catch (e) {
			console.error("Failed to load Tidal accounts:", e);
		}
	}
	function p() {
		P(c, "add"), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		}), P(u, !0), P(d, !1), P(s, !0);
	}
	async function m(e) {
		P(c, "edit");
		try {
			let t = await (await fetch(`${n()}/${e.id}`)).json();
			t?.account && (P(l, {
				id: t.account.id,
				account_name: t.account.account_name,
				client_id: t.account.client_id || "",
				client_secret: t.account.client_secret || ""
			}), P(u, !1), P(d, !1), P(s, !0));
		} catch (e) {
			console.error("Failed to load account credentials:", e);
		}
	}
	function h() {
		P(s, !1), P(u, !1), P(d, !1), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		});
	}
	async function g() {
		if (!Y(l).account_name.trim() || !Y(l).client_id.trim()) {
			console.error("Account name and Client ID are required");
			return;
		}
		if (!Y(l).client_secret.trim()) {
			console.error("Client Secret is required");
			return;
		}
		try {
			let e = {
				account_name: Y(l).account_name,
				client_id: Y(l).client_id,
				client_secret: Y(l).client_secret
			};
			Y(c) === "add" ? await fetch(`${n()}`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}) : await fetch(`${n()}/${Y(l).id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), h(), await f();
		} catch (e) {
			console.error("Failed to save account:", e);
		}
	}
	async function _(e, t) {
		try {
			await fetch(`${n()}/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await f();
		} catch (e) {
			console.error("Failed to toggle account:", e);
		}
	}
	async function v(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/${e}`, { method: "DELETE" }), await f();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function y(e) {
		try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t ? window.location.href = t : console.error("Failed to get Tidal auth URL");
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var b = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), bt();
		}
	};
	ci();
	var x = Oi(), S = dn(x), C = L(I(S), 2), w = (e) => {
		$(e, vi());
	}, ee = (e) => {
		var t = Ei(), n = dn(t), o = I(n), s = L(I(o), 2), c = I(s, !0);
		O(s), O(o);
		var l = L(o, 2), u = (e) => {
			var t = yi(), n = dn(t), r = I(n);
			$r(r);
			var a = L(r, 2);
			O(n), Be(2), ii(r, () => Y(i), (e) => P(i, e)), Z("click", a, () => {
				navigator.clipboard.writeText(Y(i)), alert("Copied to clipboard!");
			}), $(e, t);
		};
		Fr(l, (e) => {
			Y(a) || e(u);
		}), O(n);
		var d = L(n, 2), f = I(d), h = I(f), g = I(h);
		O(h);
		var b = L(h, 2), x = (e) => {
			var t = bi();
			Z("click", t, p), $(e, t);
		};
		Fr(b, (e) => {
			Y(r), X(() => Y(r).length < 25) && e(x);
		}), O(f);
		var S = L(f, 2);
		Br(S, 5, () => Y(r), Ir, (e, t) => {
			var n = wi(), r = I(n), i = I(r), a = I(i, !0);
			O(i);
			var o = L(i, 2), s = I(o), c = (e) => {
				$(e, xi());
			}, l = (e) => {
				$(e, Si());
			};
			Fr(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = L(s, 2), d = (e) => {
				$(e, Ci());
			};
			Fr(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), O(o), O(r);
			var f = L(r, 2), p = I(f), h = L(p, 2), g = I(h, !0);
			O(h);
			var b = L(h, 2);
			let x;
			var S = I(b, !0);
			O(b);
			var C = L(b, 2);
			O(f), O(n), Mn(() => {
				Tr(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), Tr(g, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), x = Yr(b, 1, "btn-ghost svelte-11pw7by", null, x, { active: Y(t).is_active }), Tr(S, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), Z("click", p, () => m(Y(t))), Z("click", h, () => y(Y(t).id)), Z("click", b, () => _(Y(t).id, Y(t).is_active)), Z("click", C, () => v(Y(t).id, Y(t).display_name || Y(t).account_name)), $(e, n);
		}, (e) => {
			$(e, Ti());
		}), O(S), O(d), Mn(() => {
			Tr(c, Y(a) ? "Expand" : "Collapse"), Tr(g, `Accounts (${(Y(r), X(() => Y(r).length)) ?? ""}/25)`);
		}), Z("click", s, () => P(a, !Y(a))), $(e, t);
	};
	Fr(C, (e) => {
		Y(o) ? e(w) : e(ee, -1);
	}), O(S);
	var te = L(S, 2), ne = (e) => {
		var n = Di(), r = I(n), i = I(r), a = I(i), o = I(a, !0);
		O(a);
		var s = L(a, 2);
		O(i);
		var f = L(i, 2), p = I(f), m = L(I(p), 2);
		$r(m), O(p);
		var _ = L(p, 2), v = L(I(_), 2);
		$r(v), O(_);
		var y = L(_, 2), b = L(I(y), 2), x = I(b);
		$r(x);
		var S = L(x, 2), C = I(S, !0);
		O(S), O(b), O(y), O(f);
		var w = L(f, 2), ee = I(w), te = L(ee, 2), ne = I(te, !0);
		O(te), O(w), O(r), O(n), Mn(() => {
			Tr(o, Y(c) === "add" ? "Add Tidal Account" : "Edit Tidal Account"), ei(x, "type", Y(d) ? "text" : "password"), Tr(C, Y(d) ? "🙈" : "👁️"), Tr(ne, Y(c) === "add" ? "Add Account" : "Save Changes");
		}), Z("click", s, h), ii(m, () => Y(l).account_name, (e) => Zt(l, Y(l).account_name = e)), ii(v, () => Y(l).client_id, (e) => Zt(l, Y(l).client_id = e)), ii(x, () => Y(l).client_secret, (e) => Zt(l, Y(l).client_secret = e)), Z("input", x, () => P(u, !0)), Z("click", S, () => P(d, !Y(d))), Z("click", ee, h), Z("click", te, g), Z("click", r, si(function(e) {
			ui.call(this, t, e);
		})), Z("click", n, h), $(e, n);
	};
	return Fr(te, (e) => {
		Y(s) && e(ne);
	}), $(e, x), Je(b);
}
customElements.define("tidal-dashboard-card", _i(Ai, { apiBase: {} }, [], [], { mode: "open" }));
//#endregion
export { Ai as default };
